# OOS v2.13 — Hacker News Pilot Query Plan

**Title:** OOS v2.13 — Hacker News Pilot Query Plan
**Status:** Draft / operational query plan
**Roadmap item:** v2.13 item 3
**Branch:** `ops/v2-13-operational-pilot-cycle-1`
**Created:** 2026-05-13
**Based on:**
- [Founder ICP and Preference Profile v2.13](founder_icp_preference_profile_v2_13.md)
- [Pilot Cycle 1 Brief v2.13](pilot_cycle_1_brief_v2_13.md)
- [HN Connector Hardening Plan](hacker_news_connector_hardening_plan.md)

---

## 1. Purpose

The purpose of the HN query plan is to collect **bounded, traceable HN evidence** for Pilot Cycle 1 focused on business-relevant pain signals aligned with founder preferences.

This is **not** broad HN scraping.
This is **not** source expansion.
This does **not** authorize live collection by itself.
Live HN collection requires **explicit founder approval**.

The query plan defines exactly what to search for, how much to collect, what to accept, what to exclude, and how to trace every item back to its source.

---

## 2. Source Scope

### Allowed HN Source

| Attribute | Value |
|-----------|-------|
| `source_id` | `hacker_news` |
| `source_type` | `discussion` |
| Access method | HN Algolia API (`hn.algolia.com/api/v1`) or fixture/manual bounded input |

### Allowed HN Content Types

| Content Type | Allowed | Notes |
|-------------|---------|-------|
| **Ask HN** | Yes | Primary signal source; explicit problem statements |
| **Show HN** | Yes — with care | Solution-first source; noise-flag self-promotion |
| **Launch HN** | Yes — with care | Promotional bias; noise-flag hype |
| **Comments** | Yes — bounded only | Must have stable `source_url`; bounded collection |
| **Search results** | Yes | For specific allowed queries only |

### Explicitly Excluded

- Broad crawling of HN front page
- User profile scraping
- Unrelated front-page scraping
- Generalized scraping outside HN Algolia / stable HN URLs

---

## 3. Pilot Focus Themes

These themes are derived from the [Founder ICP and Preference Profile](founder_icp_preference_profile_v2_13.md), Section 10 (Pilot Cycle 1 Preference Focus) and the [Pilot Cycle 1 Brief](pilot_cycle_1_brief_v2_13.md), Section 3 (Pilot Focus Themes).

| # | Focus Area | Rationale |
|---|------------|-----------|
| F-1 | **AI agents debugging / observability / reliability** | Active pain in fast-growing domain; clear ICP (developers building with AI agents) |
| F-2 | **Devtools pain around AI workflows** | High founder expertise fit; validated quickly |
| F-3 | **Data workflow / ETL / automation pain** | Repeated pain pattern; SMB and analyst ICPs |
| F-4 | **Finance / management reporting automation pain** | Clear business cost; CFO/consultant ICPs |
| F-5 | **SMB operational automation** | Broad, high-volume pain domain; reachable ICPs |
| F-6 | **Integration pain between tools** | Universal pain; clear time-loss signal |
| F-7 | **Manual reporting / reconciliation / monitoring** | Specific, repeated, costly; multiple ICPs |

---

## 4. Query Buckets

### Bucket A — AI Agent Debugging / Observability / Reliability

**Focus:** Active pain in AI agent development and operations. Developers building with agent frameworks, LLMs, automation — observability/debugging pain.

| # | Query | Intent |
|---|-------|--------|
| A-1 | "AI agent debugging" | Direct agent debugging pain |
| A-2 | "LLM agent debugging" | LLM-specific agent debugging |
| A-3 | "agent observability" | Observability tool needs |
| A-4 | "AI agents unreliable" | Reliability complaints |
| A-5 | "debugging autonomous agents" | Autonomous agent debugging pain |
| A-6 | "agent tracing" | Tracing/tooling pain |
| A-7 | "AI workflow debugging" | Broader AI workflow debugging |
| A-8 | "LLM workflows unreliable" | LLM workflow reliability complaints |

### Bucket B — Devtools around AI Workflows

**Focus:** Developer tool pain in the AI/LLM ecosystem. Testing, evaluation, prompt management, code review, and workflow integration pain.

| # | Query | Intent |
|---|-------|--------|
| B-1 | "AI developer tools pain" | Direct devtools pain |
| B-2 | "LLM development workflow" | Workflow friction |
| B-3 | "testing LLM apps" | Testing pain |
| B-4 | "evaluating LLM outputs" | Evaluation/quality pain |
| B-5 | "prompt testing" | Prompt engineering workflow pain |
| B-6 | "AI code review workflow" | Code review + AI pain |
| B-7 | "Claude Code workflow" | Specific tool workflow pain |
| B-8 | "Codex workflow" | Specific tool workflow pain |
| B-9 | "vibe coding problems" | Emerging category pain |

### Bucket C — Data Workflow / ETL / Automation Pain

**Focus:** Data pipeline, ETL, spreadsheet, and reporting automation pain. SMB and analyst ICPs.

| # | Query | Intent |
|---|-------|--------|
| C-1 | "ETL pain" | Direct ETL pain |
| C-2 | "data pipeline pain" | Pipeline management pain |
| C-3 | "data cleaning automation" | Data prep automation needs |
| C-4 | "spreadsheet automation" | Spreadsheet workflow pain |
| C-5 | "manual data entry" | Manual data entry complaints |
| C-6 | "CSV workflow" | CSV/pipeline pain |
| C-7 | "dashboard maintenance" | Dashboard upkeep burden |
| C-8 | "reporting automation" | Reporting automation pain |

### Bucket D — SMB Operations / Finance / Reporting

**Focus:** Small business operational pain, finance workflows, accounting automation, cash flow management, and management reporting.

| # | Query | Intent |
|---|-------|--------|
| D-1 | "small business reporting" | SMB reporting pain |
| D-2 | "accounting automation" | Accounting workflow pain |
| D-3 | "finance workflow" | Finance operations pain |
| D-4 | "management reporting" | Management reporting burden |
| D-5 | "cash flow spreadsheet" | Cash flow management pain |
| D-6 | "reconciliation automation" | Reconciliation pain |
| D-7 | "invoice processing" | Invoice workflow pain |
| D-8 | "operations automation" | General ops automation |

### Bucket E — Integration Pain

**Focus:** Cross-tool integration pain, API integration problems, tool syncing, and workflow automation gaps.

| # | Query | Intent |
|---|-------|--------|
| E-1 | "integration pain" | Direct integration pain |
| E-2 | "API integration problems" | API integration friction |
| E-3 | "Zapier alternatives" | Workflow automation tool gaps |
| E-4 | "workflow automation tools" | Tool search/discovery |
| E-5 | "sync data between tools" | Data sync pain |
| E-6 | "SaaS integration" | SaaS tool integration pain |
| E-7 | "webhook reliability" | Webhook reliability complaints |

### Bucket F — Ask HN Discovery

**Focus:** Ask HN posts that surface explicit needs, tool searches, pain points, and workaround discussions.

| # | Query | Intent |
|---|-------|--------|
| F-1 | "Ask HN: What are you using for" | Tool-selection discovery |
| F-2 | "Ask HN: How do you manage" | Workflow management pain |
| F-3 | "Ask HN: Alternatives to" | Tool-switching signal |
| F-4 | "Ask HN: Pain points" | Direct pain discovery |
| F-5 | "Ask HN: What is the worst part of" | Pain extraction |
| F-6 | "Ask HN: How do you automate" | Automation gap discovery |

### Bucket G — Show HN / Solution-First Signals

**Focus:** Show HN posts to detect solution patterns, alternatives, complaints in comments, and unmet needs.

> **Warning:** Show HN is solution-first, not direct pain-first. It should be used to detect solution patterns, alternatives, complaints in comments, and unmet needs. Self-promotion and launch hype must be noise-flagged.

| # | Query | Intent |
|---|-------|--------|
| G-1 | "Show HN AI agent" | AI agent solution patterns |
| G-2 | "Show HN developer tool" | Devtool solution patterns |
| G-3 | "Show HN automation" | Automation solution patterns |
| G-4 | "Show HN data pipeline" | Data pipeline solution patterns |
| G-5 | "Show HN observability" | Observability solution patterns |
| G-6 | "Show HN spreadsheet" | Spreadsheet solution patterns |
| G-7 | "Show HN finance" | Finance solution patterns |

---

## 5. Collection Parameters

### Volume Targets

| Parameter | Value |
|-----------|-------|
| Target HN raw evidence | 25–75 items |
| Minimum dry-cycle HN raw evidence | 5–15 items |
| **Maximum HN raw evidence cap** for Pilot Cycle 1 | **100 items** unless founder explicitly approves more |

### Per-Query Limits

| Parameter | Value |
|-----------|-------|
| Per-query cap | 5–10 records |
| Preferred selection | Recent and high-signal items |
| Anti-dominance rule | No single query may dominate the corpus |

### Time Window

| Parameter | Value |
|-----------|-------|
| Default window | Last 12–24 months |
| Older items allowed if | Still active/recurring and clearly relevant |
| Stale evidence treatment | Flag as potentially stale |

---

## 6. Inclusion Criteria

Include HN items/comments when they show **at least one** of:

| # | Criterion | Example Indicators |
|---|-----------|-------------------|
| I-1 | Specific actor | Named role, job title, or clear persona |
| I-2 | Specific workflow | Described steps, inputs, outputs |
| I-3 | Clear pain verb or pain pattern | "frustrating", "struggle", "nightmare", "waste of time" |
| I-4 | Repeated workaround | Scripts, spreadsheets, hacks to fill a gap |
| I-5 | Time loss | Hours/days lost to manual work |
| I-6 | Money/business cost | Explicit cost, revenue leakage, or pricing frustration |
| I-7 | Integration friction | Tools that don't work together |
| I-8 | Reliability/debugging issue | Breaking, flaky, unreliable |
| I-9 | Operational burden | Manual processes, compliance, reporting burden |
| I-10 | Tool switching / alternatives discussion | "Alternatives to X", "switched from Y to Z" |
| I-11 | Explicit complaint | Direct dissatisfaction with current solution |
| I-12 | Unmet need | "Wish there was", "someone should build", "why isn't there" |
| I-13 | Willingness to pay / paid alternatives / pricing discussion | "I'd pay for", "too expensive", "$X/month is not worth it" |

---

## 7. Exclusion / Noise Criteria

Exclude or flag as noise:

| # | Noise Pattern | Example |
|---|--------------|---------|
| N-1 | Pure hype | "AI is the future of everything" |
| N-2 | Generic "AI is cool" | Enthusiasm without pain |
| N-3 | Self-promo without pain | "Check out my new startup!" with no problem context |
| N-4 | Flamewar / meta-discussion | HN moderation debates, language wars |
| N-5 | Ideology / politics | Not a business pain domain |
| N-6 | Broad AI speculation | "AGI will change everything" |
| N-7 | Jokes / memes | Not a signal source |
| N-8 | One-off personal preference | "I don't like dark mode" |
| N-9 | Low-context comments | < 100 chars, no actor/workflow/object |
| N-10 | Duplicate launch threads | Same product posted multiple times |
| N-11 | No stable `source_url` | Missing `objectID` or malformed URL |
| N-12 | No actor/workflow/object | Vague frustration without specifics |
| N-13 | No business relevance | Hobby-only, consumer entertainment |

### Noise Handling Policy

- Do **not** silently drop if the collector keeps weak/noise records with explicit flags.
- Pilot Cycle 1 review should prioritize `accepted`/`weak` signals, not raw noise.
- Records flagged as noise should still be retained with `quality_flags` set; downstream review decides disposition.

---

## 8. Source URL Traceability

Every HN evidence item **must** have a stable `source_url`.

### URL Format

| Item Type | `source_url` Format |
|-----------|-------------------|
| Story / Ask HN / Show HN / Launch HN | `https://news.ycombinator.com/item?id={objectID}` |
| Comment | `https://news.ycombinator.com/item?id={comment_id}` |

### URL Rules

| Rule | Requirement |
|------|-------------|
| No `urn:` placeholders | Forbidden |
| No missing `source_url` | Forbidden |
| No guessed URL without source id | Forbidden |
| Missing or malformed `source_url` → | Reject before pilot run or mark as validation failure |
| Items without valid `source_url` → | Do **not** include in founder review package |

### Comment URL Handling

- Comments are HN items with their own `objectID`.
- Comment `source_url` = `https://news.ycombinator.com/item?id={comment_objectID}`.
- Parent story relationship preserved in `raw_metadata.story_id` and `raw_metadata.parent_id`.

---

## 9. Query Noise Risks

| # | Risk | Likelihood | Mitigation |
|---|------|------------|------------|
| R-1 | HN is developer-heavy; may overrepresent devtools pain | High | Focus themes include non-dev domains (SMB, finance, ops); document bias in results report |
| R-2 | Show HN has self-promotion bias | Medium | Flag self-promotion; treat as solution-pattern, not direct pain; require comments to validate |
| R-3 | AI topics have hype bias | High | Focus on specific pain keywords; exclude "AI is the future" threads; per-query caps limit dominance |
| R-4 | Ask HN can be anecdotal | Medium | Require specific actor/workflow/object for inclusion; flag low-context Ask HNs |
| R-5 | Comments can be flamewar-heavy | Medium | Low-context flag; exclude flamewar/meta patterns; prefer high-substance comments |
| R-6 | Finance/SMB topics may be underrepresented | Medium | Dedicated Bucket D targets these; document underrepresentation if it occurs |
| R-7 | Popular posts may represent curiosity, not buyer pain | Medium | Inclusion criteria require pain evidence, not just popularity; points alone is not signal |
| R-8 | HN commenters are not necessarily representative buyers | Medium | HN is one source; cross-reference with GitHub Issues and future sources; do not use HN alone for buyer validation |
| R-9 | Query keyword matches may return irrelevant items | Low-Medium | Inclusion/exclusion criteria serve as manual filter; per-query cap limits noise from any one query |

---

## 10. Expected HN Contribution to Pilot

### Expected HN Role

| Can Do | Description |
|--------|-------------|
| Discover community pain | Surface pain signals from a large, technical community |
| Reveal workaround discussions | Find people building hacks/spreadsheets/scripts to fill gaps |
| Detect solution alternatives | Surface "alternatives to X" and tool-switching discussions |
| Surface emerging AI/devtools/data automation pains | Capture bleeding-edge pain in fast-moving domains |
| Provide comment-level objections and unmet needs | Deepen understanding of why existing solutions fail |

### Expected NOT to Do

| Cannot Do | Reason |
|-----------|--------|
| Prove willingness to pay alone | HN complaints ≠ validated buyer intent |
| Validate market size | Discussion volume ≠ market size |
| Replace founder interviews | HN is observational, not interventional |
| Replace GitHub Issues evidence | Different signal types; complementary |
| Represent SMB finance pain comprehensively | HN audience skews technical; finance/SMB underrepresented |

---

## 11. HN Query Priority Table

> **Priorities:**
> - **P0** — must run in first cycle
> - **P1** — run if volume needed
> - **P2** — optional / backup

| # | Priority | Bucket | Query | Intent | Expected evidence_kind | Noise Risk | Per-Query Cap | Include If | Exclude/Flag If |
|---|----------|--------|-------|--------|------------------------|------------|---------------|------------|-----------------|
| 1 | P0 | A | "AI agent debugging" | Agent debugging pain | `pain_signal_candidate`, `complaint` | Medium | 10 | Specific actor + workflow | Hype, "AI agents are the future" |
| 2 | P0 | A | "agent observability" | Observability tool needs | `pain_signal_candidate`, `feature_request` | Medium | 10 | Specific observability gap | Product launch without pain context |
| 3 | P0 | B | "testing LLM apps" | LLM testing pain | `pain_signal_candidate`, `workaround` | Medium | 10 | Testing workflow pain described | "We built a testing tool — check it out" |
| 4 | P0 | C | "ETL pain" | Direct ETL pain | `pain_signal_candidate`, `complaint` | Low-Medium | 10 | Specific ETL workflow problem | "ETL is dead, use streaming" debate |
| 5 | P0 | C | "manual data entry" | Manual data entry complaints | `pain_signal_candidate`, `complaint` | Low | 10 | Repeated manual entry described | One-off complaint with no recurrence |
| 6 | P0 | D | "reconciliation automation" | Reconciliation pain | `pain_signal_candidate`, `workaround` | Low | 10 | Finance reconciliation pain | Generic "automate everything" |
| 7 | P0 | E | "integration pain" | Direct integration pain | `pain_signal_candidate`, `complaint` | Medium | 10 | Tools that don't work together | "API design is hard" without specific case |
| 8 | P0 | F | "Ask HN: What are you using for" | Tool-selection discovery | `pain_signal_candidate`, `complaint`, `feature_request` | Low | 10 | Clear need for tool/solution | No responses; low engagement |
| 9 | P0 | F | "Ask HN: How do you manage" | Workflow management pain | `pain_signal_candidate`, `workaround` | Low | 10 | Workflow pain with workaround | Empty thread or joke responses |
| 10 | P0 | F | "Ask HN: Alternatives to" | Tool-switching signal | `complaint`, `feature_request` | Low | 10 | Explicit dissatisfaction with current tool | "I just want to try something new" (no pain) |
| 11 | P1 | A | "debugging autonomous agents" | Autonomous agent debugging | `pain_signal_candidate`, `workaround` | Medium | 10 | Agent debugging pain described | Hype about autonomous agents |
| 12 | P1 | A | "LLM workflows unreliable" | LLM reliability complaints | `pain_signal_candidate`, `complaint` | Medium | 10 | Specific reliability failure described | "LLMs are stochastic, duh" |
| 13 | P1 | B | "evaluating LLM outputs" | Evaluation/quality pain | `pain_signal_candidate`, `workaround` | Medium | 10 | Evaluation workflow pain | "We built an eval framework" (launch) |
| 14 | P1 | B | "vibe coding problems" | Emerging category pain | `pain_signal_candidate`, `complaint` | Medium-High | 10 | Specific vibe coding pain pattern | Hype, meme, "vibe coding is the future" |
| 15 | P1 | C | "spreadsheet automation" | Spreadsheet workflow pain | `pain_signal_candidate`, `workaround` | Low-Medium | 10 | Spreadsheet-as-workaround pain | "I love spreadsheets" |
| 16 | P1 | D | "accounting automation" | Accounting workflow pain | `pain_signal_candidate`, `complaint` | Low-Medium | 10 | Specific accounting workflow pain | Generic "accounting is boring" |
| 17 | P1 | D | "small business reporting" | SMB reporting pain | `pain_signal_candidate`, `complaint` | Low-Medium | 10 | SMB reporting burden described | Enterprise ERP discussion |
| 18 | P1 | E | "Zapier alternatives" | Workflow automation tool gaps | `complaint`, `feature_request` | Medium | 10 | Specific Zapier limitation/gap | "Zapier is great" (no pain) |
| 19 | P1 | F | "Ask HN: Pain points" | Direct pain discovery | `pain_signal_candidate`, `complaint` | Low | 10 | Specific business pain described | Generic "everything is broken" |
| 20 | P1 | F | "Ask HN: How do you automate" | Automation gap discovery | `workaround`, `feature_request` | Low | 10 | Automation gap with workaround | "I use Python for everything" with no pain |
| 21 | P2 | A | "AI agents unreliable" | Agent reliability complaints | `pain_signal_candidate`, `complaint` | Medium | 10 | Specific reliability failure | "AI is unreliable in general" |
| 22 | P2 | B | "AI developer tools pain" | General devtools pain | `pain_signal_candidate`, `complaint` | Medium | 10 | Specific devtool pain | Generic "devtools are hard" |
| 23 | P2 | C | "data cleaning automation" | Data prep automation | `pain_signal_candidate`, `workaround` | Low | 10 | Data cleaning pain described | "Just use pandas" |
| 24 | P2 | D | "invoice processing" | Invoice workflow pain | `pain_signal_candidate`, `complaint` | Low | 10 | Invoice processing pain | "I use QuickBooks" (no pain) |
| 25 | P2 | D | "cash flow spreadsheet" | Cash flow management pain | `pain_signal_candidate`, `workaround` | Low | 10 | Cash flow spreadsheet pain | "Cash flow is important" (no pain) |
| 26 | P2 | E | "webhook reliability" | Webhook reliability complaints | `complaint`, `pain_signal_candidate` | Medium | 10 | Webhook reliability failure | "Just use polling instead" |
| 27 | P2 | F | "Ask HN: What is the worst part of" | Pain extraction | `pain_signal_candidate`, `complaint` | Low | 10 | Specific pain described | Blanket negativity without specifics |
| 28 | P2 | G | "Show HN AI agent" | AI agent solution patterns | `solution_pattern`, `product_launch` | High | 10 | Comments reveal pain/alternatives | Pure self-promo, no comments, no pain context |
| 29 | P2 | G | "Show HN automation" | Automation solution patterns | `solution_pattern`, `product_launch` | High | 10 | Comments reveal pain/alternatives | Launch theater, no substance |
| 30 | P2 | G | "Show HN observability" | Observability solution patterns | `solution_pattern`, `product_launch` | High | 10 | Comments reveal pain/alternatives | Self-promo without pain context |

### Priority Allocation Summary

| Priority | Queries | Description |
|----------|---------|-------------|
| P0 | 10 queries | Must run in first cycle; covers all 7 focus areas |
| P1 | 10 queries | Run if volume needed; extends coverage |
| P2 | 10 queries | Optional / backup; runs only if P0+P1 insufficient |
| **Total** | **30 queries** | 10 per priority tier |

---

## 12. HN Collection Approval Gate

This plan **does not authorize live collection**.

| Gate | Requirement |
|------|-------------|
| Live HN collection | Founder approval **required** before live HN API calls |
| Without live approval | Use manual bounded input or fixture fallback |
| Runtime outputs | Must go to explicit `output_dir` |
| Committed repository artifacts | None unless explicitly approved |

### Live Collection Approval Checklist

Before live HN collection can proceed, the founder must explicitly:

1. Confirm approval of the query plan (this document).
2. Confirm approval of live HN Algolia API access.
3. Confirm the `output_dir` for runtime artifacts (must not be a default repository path).
4. Acknowledge that collection caps (max 100 items) are in effect.

---

## 13. Dry-Cycle Fallback

If live HN collection is not approved:

| Step | Action |
|------|--------|
| 1 | Manually collect 5–15 HN URLs matching P0 queries |
| 2 | Prepare bounded input JSON manually or via approved process |
| 3 | Preserve `source_id` (`hacker_news`), `source_type` (`discussion`), and `source_url` for every item |
| 4 | Run pilot on bounded input only |

### Dry-Cycle Minimum Items

| Artifact | Minimum |
|----------|---------|
| HN raw evidence items | 5–15 |
| P0 queries covered | At least 5 of 10 P0 queries |

A dry cycle that produces fewer than 5 HN items is not a failure — but requires a documented explanation of why so few items were collected.

---

## 14. HN Review Questions for Founder

After HN evidence is collected, the founder should answer:

| # | Question | What to Assess |
|---|----------|---------------|
| Q-1 | Are the HN pains specific enough? | Actor + workflow + pain verb present |
| Q-2 | Are they too devtools-heavy? | Compare devtools vs SMB/finance/ops ratio |
| Q-3 | Are they business-relevant? | ICP alignment check |
| Q-4 | Which query buckets produced useful evidence? | Bucket performance assessment |
| Q-5 | Which query buckets produced noise? | Buckets to kill or tune for Cycle 2 |
| Q-6 | Should any HN query bucket be killed before Cycle 2? | Bucket retirement decision |
| Q-7 | Does HN need another complementary source? | Source gap identification |

---

## 15. Bucket Allocation Across Focus Areas

| Focus Area | Primary Buckets | Expected HN Contribution |
|------------|----------------|------------------------|
| F-1 AI agents debugging / observability / reliability | A, B | High — HN is strong on devtools/AI agent pain |
| F-2 Devtools pain around AI workflows | B | High — core HN audience |
| F-3 Data workflow / ETL / automation pain | C | Medium — present but not dominant |
| F-4 Finance / management reporting automation | D | Low-Medium — underrepresented on HN |
| F-5 SMB operational automation | D, E | Low-Medium — SMB owners less present |
| F-6 Integration pain between tools | E | Medium — universal pain, well-represented |
| F-7 Manual reporting / reconciliation / monitoring | C, D | Low-Medium — crossed with data/finance pain |

### Bias Awareness

HN skews toward developers and technical founders. Focus areas F-4 and F-5 (finance/SMB) are expected to be **underrepresented** relative to F-1 and F-2 (devtools/AI). This bias should be:

1. **Documented** in the pilot results report.
2. **Cross-referenced** with GitHub Issues evidence (which may have different audience bias).
3. **Considered** in any source expansion planning — non-technical audiences require non-HN sources.

---

## 16. Integration with HN Connector Hardening Plan

This query plan references the [HN Connector Hardening Plan](hacker_news_connector_hardening_plan.md) for:

- HN item → `RawEvidence` field mapping (Section 6)
- `evidence_kind` classification heuristics (Section 7)
- `source_url` traceability rules (Section 8)
- Noise and quality filters (Section 10)
- Controlled smoke plan (Section 13)

The hardening plan addresses implementation-level concerns (field mapping, classification, deduplication). This query plan addresses **operational** concerns (what to collect, how much, what to accept/reject).

Both plans are mutually reinforcing. The query plan defines what queries to run; the hardening plan defines how the adapter processes HN data.

---

## 17. Self-Audit Checklist

- [x] **Title and status present** (header)
- [x] **Purpose stated** (Section 1)
- [x] **Source scope defined** (Section 2): HN Algolia API or fixture; content types enumerated; exclusions explicit
- [x] **Pilot focus themes defined** (Section 3): 7 themes from ICP and brief
- [x] **Query buckets defined** (Section 4): 7 buckets (A–G) with numbered queries
- [x] **Collection parameters defined** (Section 5): volume targets, per-query caps, time window
- [x] **Inclusion criteria defined** (Section 6): 13 criteria
- [x] **Exclusion/noise criteria defined** (Section 7): 13 noise patterns with handling policy
- [x] **Source URL traceability defined** (Section 8): URL format, rules, comment policy
- [x] **Query noise risks documented** (Section 9): 9 risks with likelihood and mitigation
- [x] **Expected HN contribution defined** (Section 10): can do / cannot do split
- [x] **Query priority table present** (Section 11): 30 query rows with all required columns (priority, bucket, query, intent, expected evidence_kind, noise risk, per-query cap, include if, exclude/flag if)
- [x] **At least 20 queries listed** (Section 11): 30 queries (10 P0 + 10 P1 + 10 P2)
- [x] **Approval gates explicit** (Section 12): live collection requires founder approval; checklist
- [x] **Dry-cycle fallback defined** (Section 13): 5–15 manual URLs, bounded input process
- [x] **HN review questions for founder defined** (Section 14): 7 questions
- [x] **Bucket-to-focus-area cross-reference** (Section 15): bias awareness documented
- [x] **Integration with hardening plan** (Section 16): mutual reinforcement noted
- [x] **No implementation directives**: document is operational planning only
- [x] **No live API authorization**: explicit approval gate preserved
- [x] **No source code, test, script, or artifact modifications**

---

## 18. Definition of Done

Item 3 is done when:

- [x] **3.1** HN query plan exists at `docs/decisions/hacker_news_pilot_query_plan_v2_13.md`
- [x] **3.2** Query buckets are defined (7 buckets: A–G)
- [x] **3.3** At least 20 queries are listed (30 queries across 3 priority tiers)
- [x] **3.4** Collection caps are defined (25–75 target; max 100; 5–10 per query)
- [x] **3.5** Inclusion criteria are defined (13 criteria)
- [x] **3.6** Exclusion/noise criteria are defined (13 noise patterns + policy)
- [x] **3.7** `source_url` policy is explicit (format, rules, comment handling)
- [x] **3.8** Approval gates are explicit (live collection requires founder approval)
- [x] **3.9** Dry fallback is defined (5–15 manual URLs, bounded input)
- [x] **3.10** HN review questions for founder defined (7 questions)
- [x] **3.11** Query noise risks documented (9 risks)
- [x] **3.12** Query priority table has all required columns
- [x] **3.13** Priority allocation summary present
- [ ] **3.14** `.\scripts\dev-git-check.ps1` passes
- [ ] **3.15** One local commit exists with message: `[v2.13] 3 define hacker news query plan`

---

*Hacker News Pilot Query Plan v2.13. Operational planning document. Does not authorize live collection. Does not modify source code, tests, scripts, or pipeline behavior.*
