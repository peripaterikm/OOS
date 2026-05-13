# OOS v2.13 — GitHub Issues Repo Allowlist and Query Plan

**Title:** OOS v2.13 — GitHub Issues Repo Allowlist and Query Plan
**Status:** Draft / operational query plan
**Roadmap item:** v2.13 item 4
**Branch:** `ops/v2-13-operational-pilot-cycle-1`
**Created:** 2026-05-13
**Based on:**
- [Founder ICP and Preference Profile v2.13](founder_icp_preference_profile_v2_13.md)
- [Pilot Cycle 1 Brief v2.13](pilot_cycle_1_brief_v2_13.md)
- [GitHub Issues Connector Hardening Plan](github_issues_connector_hardening_plan.md)
- [HN Pilot Query Plan v2.13](hacker_news_pilot_query_plan_v2_13.md)

---

## 1. Purpose

The purpose of the GitHub Issues plan is to collect **bounded, traceable technical and workflow-pain evidence** from selected repositories aligned with founder preferences.

This is **not** broad GitHub search.
This is **not** source expansion.
This does **not** authorize live GitHub API access by itself.
Live collection requires **explicit founder approval**.

The query plan defines exactly which repositories to query, what issue search logic to use, how much to collect, what to accept, what to exclude, and how to trace every item back to its source.

---

## 2. Source Scope

### Allowed Source

| Attribute | Value |
|-----------|-------|
| `source_id` | `github_issues` |
| `source_type` | `issue_tracker` |
| Access method | GitHub Issues API / fixture / manual bounded input |

### Required Constraints

| # | Constraint |
|---|-----------|
| C-1 | Issues only — pull requests **excluded** |
| C-2 | `source_url` must be real GitHub `html_url` |
| C-3 | No `github://` fallback |
| C-4 | No missing `source_url` |
| C-5 | No placeholder URLs |
| C-6 | No repository outside approved allowlist |
| C-7 | No broad org-wide scraping unless explicitly approved |

### Content Types

| Content Type | Allowed | Notes |
|-------------|---------|-------|
| **Open issues** | Yes | Primary signal source; active pain |
| **Closed issues** | Yes — with care | Must contain strong pain/workaround/evidence; flag as stale/closed |
| **Issue comments** | No — deferred | Comment count captured in metadata; comment content not fetched by default |
| **Pull requests** | **No** | Excluded entirely; `pull_request` key filter mandatory |

### Explicitly Excluded

- Pull requests (`pull_request` key present and non-empty)
- Dependency update bot issues (dependabot, renovate, etc.)
- Release/changelog tasks
- Org-wide search without approved repo list
- PR search
- User scraping
- Private repositories
- Credentialed data beyond approved public issue access

---

## 3. Repo Selection Principles

Repositories included in the allowlist must satisfy these selection criteria:

| # | Principle | Description |
|---|-----------|-------------|
| P-1 | **Theme relevance** | Repo must be relevant to Pilot Cycle 1 themes (Section 5) |
| P-2 | **Pain likelihood** | Repo must produce issues likely to contain workflow pain, integration pain, debugging pain, reliability pain, or automation pain |
| P-3 | **Activity sufficiency** | Repo should have enough issue activity to yield useful evidence |
| P-4 | **Legal/ethical safety** | Repo should be legally and ethically safe to inspect as public issue data |
| P-5 | **ICP/buyer connection** | Repo should be connected to a plausible buyer/ICP or professional workflow |
| P-6 | **No popularity bias** | Repo should not be included just because it is popular |
| P-7 | **Corpus balance** | No single repo may dominate the corpus; per-repo caps are mandatory |

---

## 4. Pilot Focus Themes

These themes are derived from the [Founder ICP and Preference Profile](founder_icp_preference_profile_v2_13.md), Section 10 (Pilot Cycle 1 Preference Focus) and the [Pilot Cycle 1 Brief](pilot_cycle_1_brief_v2_13.md), Section 3 (Pilot Focus Themes).

### Primary GitHub Themes

| # | Focus Area | Rationale | GitHub Relevance |
|---|------------|-----------|-----------------|
| F-1 | **AI agents debugging / observability / reliability** | Active pain in fast-growing domain; clear ICP (developers building with AI agents) | High — AI/agent framework repos produce active debugging/reliability issues |
| F-2 | **LLM app testing / evaluation / prompt testing** | High founder expertise fit; validated quickly | High — eval/observability tool repos rich in testing/evaluation pain |
| F-3 | **Devtools pain around AI workflows** | High founder expertise fit; validated quickly | High — devtool repos surface integration and workflow pain |
| F-4 | **Data workflow / ETL / orchestration pain** | Repeated pain pattern; SMB and analyst ICPs | Medium-High — data/ETL repos produce pipeline and integration pain |
| F-5 | **Automation / integration workflow pain** | Universal pain; clear time-loss signal | High — automation/integration repos surface tool-connection pain |
| F-6 | **Monitoring / reliability / traceability** | Specific, repeated, costly; multiple ICPs | Medium-High — observability repos surface monitoring gaps |
| F-7 | **Finance / reporting / reconciliation automation** | Clear business cost; CFO/consultant ICPs | Medium — finance/ERP repos produce operational pain; underrepresented relative to devtools |

---

## 5. Proposed Repo Allowlist

> **Verification status:** All repositories listed below are proposed candidates. Exact repository names, issue activity levels, and pain-signal yield have **not** been verified live in this planning item. Every repo is marked `verification_required = true`. Do not claim live verification was performed.

### Priority Tiers

| Tier | Meaning | Description |
|------|---------|-------------|
| **P0** | First-cycle core | Must be included in Cycle 1; highest expected signal yield |
| **P1** | Use if volume needed | Include if P0 repos do not produce sufficient evidence |
| **P2** | Backup / optional | Include only if P0+P1 still insufficient; or as replacement for noisy P0/P1 repos |

---

### Group A: AI Agent / LLM Workflow Frameworks

Repos in this group are expected to surface debugging, reliability, observability, tool-calling, and workflow orchestration pain from developers building with AI agents and LLMs.

| # | Priority | Repo | Theme | Rationale | Expected evidence_kind | Expected pain patterns | Noise risks | Per-repo cap | Include if | Exclude/flag if | Verification required | Founder approval required |
|---|----------|------|-------|-----------|------------------------|----------------------|-------------|-------------|------------|-----------------|----------------------|--------------------------|
| A-1 | P0 | `langchain-ai/langchain` | AI agent / LLM workflow | Dominant AI framework; issues reveal debugging, integration, reliability pain | `bug_report`, `pain_signal_candidate`, `workaround` | Agent debugging, tool calling failures, integration friction, observability gaps | High issue volume; many housekeeping/chore issues; version migration noise | 10 | Specific workflow/debugging pain described | Chore/migration issue, bot-generated, dependency update | true | true |
| A-2 | P0 | `langchain-ai/langgraph` | AI agent / LLM workflow | Agent orchestration framework; issues reveal state management, graph execution, debugging pain | `bug_report`, `pain_signal_candidate`, `feature_request` | State management pain, graph debugging, execution reliability | Medium — smaller repo than langchain core | 10 | Agent orchestration pain with specific failure mode | Feature wishlist without pain context | true | true |
| A-3 | P1 | `microsoft/autogen` | AI agent / LLM workflow | Multi-agent framework; issues reveal multi-agent coordination, conversation management pain | `bug_report`, `pain_signal_candidate`, `workaround` | Multi-agent coordination, conversation state, tool integration | Medium — Microsoft-maintained; some enterprise noise | 5 | Multi-agent coordination pain described | Enterprise deployment question without pain | true | true |
| A-4 | P1 | `crewAIInc/crewAI` | AI agent / LLM workflow | Agent orchestration with role-based agents; issues reveal orchestration and task delegation pain | `bug_report`, `pain_signal_candidate`, `feature_request` | Task delegation, agent role management, execution flow | Medium — newer project; issue volume may be lower | 5 | Orchestration/task pain with specific failure | Generic "it doesn't work" without detail | true | true |
| A-5 | P2 | `run-llama/llama_index` | AI agent / LLM workflow | Data framework for LLM apps; issues reveal data ingestion, retrieval, and indexing pain | `bug_report`, `pain_signal_candidate`, `workaround` | Data ingestion pain, retrieval quality, indexing performance | High issue volume; many integration/docs issues | 5 | Data pipeline pain within LLM context | Documentation request without pain | true | true |
| A-6 | P2 | `BerriAI/litellm` | AI agent / LLM workflow | LLM proxy/cost-tracking; issues reveal multi-provider integration, cost management, reliability pain | `bug_report`, `pain_signal_candidate`, `complaint` | Multi-provider integration, rate limiting, cost tracking | Medium — focused tool; signal may be narrow | 5 | Provider integration/reliability pain | Configuration question without pain | true | true |

---

### Group B: LLM Observability / Eval / Testing

Repos in this group are expected to surface testing, evaluation, prompt management, tracing, and observability pain from developers building and operating LLM applications.

| # | Priority | Repo | Theme | Rationale | Expected evidence_kind | Expected pain patterns | Noise risks | Per-repo cap | Include if | Exclude/flag if | Verification required | Founder approval required |
|---|----------|------|-------|-----------|------------------------|----------------------|-------------|-------------|------------|-----------------|----------------------|--------------------------|
| B-1 | P0 | `langfuse/langfuse` | LLM observability / eval / testing | Open-source LLM observability; issues reveal tracing, evaluation, and monitoring pain | `bug_report`, `pain_signal_candidate`, `feature_request` | Tracing gaps, eval pipeline pain, monitoring blind spots | Medium — observability tool; some self-referential noise | 10 | Observability/eval pain with specific gap described | "Add support for X provider" without pain context | true | true |
| B-2 | P0 | `promptfoo/promptfoo` | LLM observability / eval / testing | Prompt testing and evaluation framework; issues reveal testing workflow and eval quality pain | `bug_report`, `pain_signal_candidate`, `workaround` | Prompt testing pain, eval metric gaps, comparison workflow friction | Low-Medium — focused eval tool; relevant signal | 10 | Testing/eval workflow pain described | Generic feature request without pain | true | true |
| B-3 | P1 | `Arize-ai/phoenix` | LLM observability / eval / testing | AI observability platform; issues reveal observability, tracing, and monitoring pain | `bug_report`, `pain_signal_candidate`, `feature_request` | Tracing gaps, observability blind spots, monitoring workflow | Medium — observability tool; some enterprise noise | 5 | Observability gap with specific failure | Enterprise deployment/config question without pain | true | true |
| B-4 | P1 | `traceloop/openllmetry` | LLM observability / eval / testing | OpenTelemetry for LLMs; issues reveal instrumentation, tracing standards, and observability pain | `bug_report`, `pain_signal_candidate`, `workaround` | Instrumentation pain, tracing standards gaps, OTEL integration | Low-Medium — niche observability; signal may be narrow | 5 | Instrumentation/tracing pain with specific gap | Standards discussion without pain | true | true |
| B-5 | P2 | `openai/evals` | LLM observability / eval / testing | OpenAI eval framework; issues reveal evaluation methodology and benchmarking pain | `bug_report`, `pain_signal_candidate`, `feature_request` | Eval methodology gaps, benchmark reliability, scoring pain | Medium — mostly eval framework issues; signal relevance varies | 5 | Eval methodology/reliability pain | Benchmark addition request without pain | true | true |

---

### Group C: Data Workflows / ETL / Orchestration

Repos in this group are expected to surface data pipeline, ETL, transformation, scheduling, and orchestration pain. Relevant to SMB, analyst, and data-team ICPs.

| # | Priority | Repo | Theme | Rationale | Expected evidence_kind | Expected pain patterns | Noise risks | Per-repo cap | Include if | Exclude/flag if | Verification required | Founder approval required |
|---|----------|------|-------|-----------|------------------------|----------------------|-------------|-------------|------------|-----------------|----------------------|--------------------------|
| C-1 | P0 | `dbt-labs/dbt-core` | Data workflows / ETL / orchestration | Data transformation standard; issues reveal transformation, testing, and data quality pain | `bug_report`, `pain_signal_candidate`, `workaround` | SQL transformation pain, data testing gaps, pipeline reliability | Medium — large community; many feature requests | 10 | Data transformation/testing pain with specific failure | "Add adapter for X database" without pain | true | true |
| C-2 | P0 | `apache/airflow` | Data workflows / ETL / orchestration | Dominant workflow orchestrator; issues reveal scheduling, DAG management, and operational pain | `bug_report`, `pain_signal_candidate`, `complaint` | Scheduling pain, DAG complexity, operational overhead | High — large project; many edge-case bugs and config issues | 10 | Scheduling/orchestration pain with operational impact | Configuration question, "how do I" without pain | true | true |
| C-3 | P1 | `dagster-io/dagster` | Data workflows / ETL / orchestration | Modern data orchestrator; issues reveal asset-based orchestration, observability, and dev workflow pain | `bug_report`, `pain_signal_candidate`, `feature_request` | Asset orchestration pain, dev workflow friction, observability gaps | Medium — growing project; some cloud/enterprise noise | 5 | Orchestration/dev workflow pain with specific gap | Cloud/enterprise deployment question without pain | true | true |
| C-4 | P1 | `PrefectHQ/prefect` | Data workflows / ETL / orchestration | Modern workflow orchestration; issues reveal workflow management, observability, and deployment pain | `bug_report`, `pain_signal_candidate`, `workaround` | Workflow management pain, deployment friction, monitoring gaps | Medium — Python-focused; may overrepresent Python-specific pain | 5 | Workflow/deployment pain with specific failure | "How do I deploy to X" without pain | true | true |
| C-5 | P2 | `meltano/meltano` | Data workflows / ETL / orchestration | ELT platform; issues reveal data integration, connector, and pipeline management pain | `bug_report`, `pain_signal_candidate`, `workaround` | Connector/integration pain, pipeline management friction | Low-Medium — smaller community; signal may be limited | 5 | Connector/integration pain with specific gap | "Add connector for X" without pain context | true | true |

---

### Group D: Automation / Integrations / Workflow Tools

Repos in this group are expected to surface cross-tool integration, workflow automation, and operational orchestration pain. Relevant to operations, SMB, and automation ICPs.

| # | Priority | Repo | Theme | Rationale | Expected evidence_kind | Expected pain patterns | Noise risks | Per-repo cap | Include if | Exclude/flag if | Verification required | Founder approval required |
|---|----------|------|-------|-----------|------------------------|----------------------|-------------|-------------|------------|-----------------|----------------------|--------------------------|
| D-1 | P0 | `n8n-io/n8n` | Automation / integrations / workflow tools | Fair-code workflow automation; issues reveal workflow automation, connector, and integration pain | `bug_report`, `pain_signal_candidate`, `feature_request` | Connector gaps, workflow automation friction, integration reliability | Medium — growing community; some self-host deployment noise | 10 | Connector/integration/workflow pain with specific gap | Self-host deployment question without pain | true | true |
| D-2 | P1 | `activepieces/activepieces` | Automation / integrations / workflow tools | Open-source automation (Zapier alternative); issues reveal automation gaps, integration pain, and no-code workflow friction | `bug_report`, `pain_signal_candidate`, `feature_request` | No-code automation gaps, integration friction, piece/connector pain | Low-Medium — newer project; issue volume may be lower | 5 | Automation/integration pain with specific workflow gap | "Add piece for X" without pain context | true | true |
| D-3 | P2 | `huginn/huginn` | Automation / integrations / workflow tools | Self-hosted automation agents; issues reveal automation, monitoring, and agent orchestration pain | `bug_report`, `pain_signal_candidate`, `workaround` | Agent orchestration pain, monitoring gaps, automation reliability | Medium — mature project; some stale/closed issues | 5 | Automation/monitoring pain with specific failure | Stale issue with no activity > 2 years | true | true |

---

### Group E: Finance / Operations / Reporting Adjacent Open-Source Tools

Repos in this group are expected to surface SMB financial operations, accounting, invoicing, and reporting pain. These repos are **selectively included** to capture non-developer operational pain aligned with finance/SMB ICPs. GitHub is inherently developer-heavy; SMB finance pain will be underrepresented relative to devtools pain.

| # | Priority | Repo | Theme | Rationale | Expected evidence_kind | Expected pain patterns | Noise risks | Per-repo cap | Include if | Exclude/flag if | Verification required | Founder approval required |
|---|----------|------|-------|-----------|------------------------|----------------------|-------------|-------------|------------|-----------------|----------------------|--------------------------|
| E-1 | P1 | `frappe/erpnext` | Finance / operations / reporting | Open-source ERP; issues reveal SMB operational, accounting, inventory, and reporting pain | `bug_report`, `pain_signal_candidate`, `feature_request` | Accounting/reporting pain, inventory management friction, compliance gaps | Medium-High — large ERP; many localization and config issues | 5 | SMB operational/accounting pain with business impact | Localization request for specific country without pain pattern | true | true |
| E-2 | P1 | `firefly-iii/firefly-iii` | Finance / operations / reporting | Personal finance manager; issues reveal budgeting, reporting, and financial data management pain | `bug_report`, `pain_signal_candidate`, `feature_request` | Budgeting/reporting pain, financial data import/export friction | Medium — personal finance tool; may overrepresent individual vs business pain | 5 | Financial management/reporting pain with business relevance | Personal finance feature request without business ICP connection | true | true |
| E-3 | P2 | `invoiceninja/invoiceninja` | Finance / operations / reporting | Open-source invoicing; issues reveal invoicing, payment, and SMB financial workflow pain | `bug_report`, `pain_signal_candidate`, `feature_request` | Invoicing/payment workflow pain, SMB financial friction | Medium — invoicing tool; signal may be narrow | 3 | Invoicing/SMB financial workflow pain with business impact | Payment gateway add request without pain | true | true |

---

### Allowlist Summary

| Group | Priority | Count | Description |
|-------|----------|-------|-------------|
| A — AI Agent / LLM Workflow Frameworks | P0: 2, P1: 2, P2: 2 | 6 | AI agent debugging, orchestration, tool-calling pain |
| B — LLM Observability / Eval / Testing | P0: 2, P1: 2, P2: 1 | 5 | LLM testing, evaluation, observability, tracing pain |
| C — Data Workflows / ETL / Orchestration | P0: 2, P1: 2, P2: 1 | 5 | Data pipeline, ETL, orchestration, transformation pain |
| D — Automation / Integrations / Workflow Tools | P0: 1, P1: 1, P2: 1 | 3 | Workflow automation, integration, connector pain |
| E — Finance / Operations / Reporting | P0: 0, P1: 2, P2: 1 | 3 | SMB finance, accounting, reporting, invoicing pain |
| **Total** | | **22** | |

---

## 6. Recommended First-Cycle Repo Subset

The full allowlist of 22 repos is a candidate universe. **Cycle 1 should use a smaller subset** to keep the pilot bounded, inspectable, and manageable.

### Selection Principles

- 8–12 repos maximum for Cycle 1
- Mix across AI agents / LLM workflows, observability/eval/testing, data workflow, automation/integration
- Avoid including too many finance/ERP repos unless founder explicitly wants that focus
- P0 repos are prioritized; P1 repos fill gaps; P2 repos are not included in first cycle unless volume requires

### Recommended First-Cycle Shape

| Domain | Target Count | Repos |
|--------|-------------|-------|
| AI agent / LLM workflow | 3–4 | `langchain-ai/langchain`, `langchain-ai/langgraph`, `microsoft/autogen`, `crewAIInc/crewAI` |
| Observability / eval / testing | 2–3 | `langfuse/langfuse`, `promptfoo/promptfoo`, `Arize-ai/phoenix` |
| Data / automation / integration | 2–3 | `dbt-labs/dbt-core`, `apache/airflow`, `n8n-io/n8n` |
| Finance / ops | 0–2 | `frappe/erpnext`, `firefly-iii/firefly-iii` |

### Recommended First-Cycle Repos (10 repos)

| # | Priority | Repo | Group | Theme |
|---|----------|------|-------|-------|
| 1 | P0 | `langchain-ai/langchain` | A | AI agent / LLM workflow |
| 2 | P0 | `langchain-ai/langgraph` | A | AI agent / LLM workflow |
| 3 | P0 | `langfuse/langfuse` | B | LLM observability / eval / testing |
| 4 | P0 | `promptfoo/promptfoo` | B | LLM observability / eval / testing |
| 5 | P0 | `dbt-labs/dbt-core` | C | Data workflows / ETL / orchestration |
| 6 | P0 | `apache/airflow` | C | Data workflows / ETL / orchestration |
| 7 | P0 | `n8n-io/n8n` | D | Automation / integrations / workflow tools |
| 8 | P1 | `microsoft/autogen` | A | AI agent / LLM workflow |
| 9 | P1 | `Arize-ai/phoenix` | B | LLM observability / eval / testing |
| 10 | P1 | `frappe/erpnext` | E | Finance / operations / reporting |

### First-Cycle Domain Mix

| Domain | Count | Percentage |
|--------|-------|-----------|
| AI agent / LLM workflow | 3 | 30% |
| LLM observability / eval / testing | 3 | 30% |
| Data workflows / ETL / orchestration | 2 | 20% |
| Automation / integrations | 1 | 10% |
| Finance / operations / reporting | 1 | 10% |
| **Total** | **10** | **100%** |

### Reserve Repos (P1/P2 — promote to cycle if volume insufficient)

| # | Priority | Repo | Group |
|---|----------|------|-------|
| R1 | P1 | `crewAIInc/crewAI` | A |
| R2 | P1 | `dagster-io/dagster` | C |
| R3 | P1 | `PrefectHQ/prefect` | C |
| R4 | P1 | `activepieces/activepieces` | D |
| R5 | P1 | `firefly-iii/firefly-iii` | E |
| R6 | P1 | `traceloop/openllmetry` | B |
| R7 | P2 | `run-llama/llama_index` | A |
| R8 | P2 | `BerriAI/litellm` | A |
| R9 | P2 | `openai/evals` | B |
| R10 | P2 | `meltano/meltano` | C |
| R11 | P2 | `huginn/huginn` | D |
| R12 | P2 | `invoiceninja/invoiceninja` | E |

---

## 7. Collection Parameters

### Volume Targets

| Parameter | Value |
|-----------|-------|
| Target GitHub raw evidence | 25–75 items |
| Minimum dry-cycle GitHub raw evidence | 5–15 items |
| **Maximum GitHub raw evidence cap** for Pilot Cycle 1 | **100 items** unless founder explicitly approves more |

### Per-Repo Caps

| Tier | Default cap |
|------|-------------|
| P0 repos | Up to 10 issues per repo |
| P1 repos | 3–5 issues per repo |
| P2 repos | 3–5 issues per repo |
| **Anti-dominance rule** | No single repo may contribute more than 25% of GitHub evidence without founder approval |

### Time Window

| Parameter | Value |
|-----------|-------|
| Default window | Last 12–24 months (`created:>=YYYY-MM-DD` or `updated:>=YYYY-MM-DD`) |
| Older issues allowed if | Still active/recurring and clearly relevant to pilot themes |
| Stale evidence treatment | Flag as potentially stale; document age in metadata |

### Issue State

| State | Policy |
|-------|--------|
| **Open issues** | Preferred — active pain |
| **Closed issues** | Allowed if they contain strong pain/workaround/evidence |
| **Closed/wontfix/not_planned** | Must be flagged; only include if pain description is rich and reusable |
| **Stale issues** (>365 days no update) | Flag as `stale_issue`; include only if pain pattern is clearly recurring |

---

## 8. Issue Search Logic

> **This section defines query patterns but does not execute them.** No live GitHub API calls are authorized by this plan.

### Common Filters

All queries must include these base filters:

```
is:issue
-is:pr
```

Per-repo queries add:

```
repo:<owner>/<repo>
```

Time-window queries add (when approved):

```
created:>=YYYY-MM-DD
updated:>=YYYY-MM-DD
```

Label filters where useful:

```
label:bug
label:enhancement
label:needs-triage
```

### Pain-Oriented Keywords

Keywords targeting general workflow and operational pain:

| Category | Keywords |
|----------|----------|
| Defect/reliability | `bug`, `broken`, `unreliable`, `flaky`, `timeout`, `error`, `crash`, `fails` |
| Debugging/observability | `debug`, `trace`, `log`, `observability`, `monitor`, `hard to debug`, `difficult` |
| Testing/evaluation | `test`, `evaluation`, `eval`, `scoring`, `benchmark`, `compare`, `quality` |
| Integration/connector | `integration`, `connector`, `sync`, `connect`, `compatibility`, `api`, `webhook` |
| Data/pipeline | `pipeline`, `workflow`, `ETL`, `export`, `import`, `transform`, `migration` |
| Manual/reporting | `manual`, `spreadsheet`, `CSV`, `dashboard`, `report`, `reconciliation`, `audit` |
| Workflow/automation | `workflow`, `automation`, `orchestration`, `scheduling`, `trigger` |
| Pain expressions | `frustrating`, `pain`, `struggle`, `nightmare`, `waste of time`, `hours of`, `blocker`, `critical`, `showstopper`, `can't`, `unusable` |
| Workaround signals | `workaround`, `hack`, `script`, `manual process`, `temporary`, `makeshift`, `duct tape` |

### AI/LLM-Specific Keywords

Keywords targeting AI/LLM development pain:

| Category | Keywords |
|----------|----------|
| Agent | `agent`, `tool calling`, `function calling`, `multi-agent`, `orchestration`, `autonomous` |
| LLM behavior | `hallucination`, `context window`, `token`, `prompt`, `streaming`, `structured output`, `retry` |
| Eval/testing | `eval`, `evaluation`, `promptfoo`, `benchmark`, `accuracy`, `regression` |
| Observability | `trace`, `span`, `observability`, `monitoring`, `dashboard`, `cost tracking` |
| Memory/state | `memory`, `state`, `context`, `conversation`, `history`, `persistence` |
| Reliability | `retry`, `fallback`, `timeout`, `rate limit`, `throttle`, `failover` |

### Per-Repo Query Templates

For each repo in the first-cycle subset, queries should follow these templates:

**Template 1 — Bug/pain search (label-based):**
```
is:issue -is:pr repo:<owner>/<repo> label:bug created:>=2024-01-01
```
Then post-filter for pain keywords in title/body.

**Template 2 — Enhancement/feature gap search (label-based):**
```
is:issue -is:pr repo:<owner>/<repo> label:enhancement created:>=2024-01-01
```
Then post-filter for need/workaround/pain language.

**Template 3 — Pain keyword search (full-text):**
```
is:issue -is:pr repo:<owner>/<repo> (pain OR frustrating OR broken OR blocker OR workaround OR "hard to" OR "can't" OR nightmare) created:>=2024-01-01
```

**Template 4 — Integration/reliability pain search:**
```
is:issue -is:pr repo:<owner>/<repo> (integration OR connector OR sync OR reliability OR flaky OR timeout OR "doesn't work with" OR incompatible) created:>=2024-01-01
```

**Template 5 — AI-specific pain search (for AI/LLM repos only):**
```
is:issue -is:pr repo:<owner>/<repo> (agent OR "tool calling" OR hallucination OR eval OR prompt OR trace OR streaming OR "structured output" OR retry) created:>=2024-01-01
```

### Prohibited Search Patterns

| Pattern | Reason |
|---------|--------|
| Broad GitHub-wide search without `repo:` qualifier | Violates repo allowlist boundary |
| Org-wide search (`org:`) | Unless explicitly approved for a specific org |
| PR search (`is:pr`) | PRs are excluded from GitHub Issues evidence |
| User scraping (`author:`) | Privacy concern; not needed for pain discovery |
| Private repo search | Out of scope; only public repos |
| Search without `is:issue` | Risk of PR contamination |

---

## 9. Inclusion Criteria

Include GitHub issues when they show **at least one** of:

| # | Criterion | Example Indicators |
|---|-----------|-------------------|
| I-1 | Clear bug / defect / failure | Bug label + specific reproduction steps or impact |
| I-2 | Feature gap / workflow pain | Enhancement label + described workflow gap with business/user impact |
| I-3 | Repeated failure mode | Multiple reports of same issue; recurring problem pattern |
| I-4 | Integration friction | Tools/APIs that don't work together; connector gaps |
| I-5 | Debugging / observability problem | Difficulty tracing, monitoring, or understanding system behavior |
| I-6 | Missing functionality causing workaround | User describes manual workaround for missing feature |
| I-7 | Reliability issue | Flaky, unstable, timeout, intermittent failure with production impact |
| I-8 | Production or team impact | Multiple users affected; blocking deployment or workflow |
| I-9 | Manual operational burden | Manual steps, spreadsheet work, script-based workaround |
| I-10 | Issue comments indicating multiple affected users | "+1", "same here", "also experiencing this", multiple reporters |
| I-11 | Labels indicating maintainer-acknowledged signal | `bug`, `enhancement`, `needs-triage`, `help wanted` |
| I-12 | Explicit workaround described | "I wrote a script to...", "Currently we manually...", "As a workaround..." |
| I-13 | Clear actor/workflow/object | Specific role, described workflow steps, identifiable tool/system |

---

## 10. Exclusion / Noise Criteria

Exclude or flag as noise:

| # | Noise Pattern | Example | Action |
|---|--------------|---------|--------|
| N-1 | Pull request | `pull_request` key present | **Drop** — not an issue |
| N-2 | Dependency update bot | dependabot, renovate, pyup, greenkeeper | Flag `bot_generated`; include only if exceptional pain context |
| N-3 | Release/changelog task | "Release v2.5.0", "Update changelog" | Flag `maintainer_housekeeping`; usually exclude |
| N-4 | Stale without evidence | Open > 365 days, no comments, no reactions | Flag `stale_issue`; exclude unless recurring |
| N-5 | Duplicate with no extra evidence | Labeled `duplicate`, links to another issue | Flag `duplicate_or_invalid`; exclude unless adds new pain detail |
| N-6 | Invalid/wontfix with no reusable pain | Labeled `invalid` or `wontfix`, `state_reason: not_planned` | Flag `wontfix_or_not_planned`; include only if pain description is rich |
| N-7 | Low-context "does not work" without details | "< 200 chars body, no reproduction, no impact" | Flag `low_text_context`; exclude unless strong title signal |
| N-8 | Personal setup issue with no recurrence | "Can't install on my machine", specific env | Flag `low_text_context`; exclude unless pattern emerges |
| N-9 | Pure feature wishlist without pain | "It would be cool if...", "Add support for X" with no pain context | Flag `requires_manual_review`; deprioritize |
| N-10 | Support request unrelated to Pilot focus | "How do I configure X?", "Where is the documentation for Y?" | Flag `requires_manual_review`; exclude unless reveals doc/UX gap |
| N-11 | No `html_url` | Missing or empty `html_url` in source data | **Drop** — violates source URL traceability |
| N-12 | No stable `source_url` | URL pattern doesn't match `https://github.com/<owner>/<repo>/issues/<number>` | **Drop** — cannot trace |
| N-13 | No actor/workflow/object | Vague frustration without specifics | Flag `low_text_context`; exclude |
| N-14 | No business relevance | Hobby project issue, personal preference, entertainment | Flag `requires_manual_review`; exclude |
| N-15 | Housekeeping/maintainer chore | Title matches `^(chore|build|ci|test|refactor|docs|style)(\(.*\))?:` | Flag `maintainer_housekeeping`; exclude |

### Noise Handling Policy

- **PRs are dropped** (counted in `pr_filtered_count`)
- **Missing `html_url` drops** (counted in `missing_url_count`)
- All other noise items are **flagged with `quality_flags`** but retained in records
- Downstream review prioritizes accepted/weak signals over noise-flagged items
- The source quality report tracks noise rates per repo

---

## 11. Source URL Traceability

Every GitHub evidence item **must** have a stable `source_url`.

### URL Format

| Item Type | `source_url` Format |
|-----------|-------------------|
| GitHub Issue | `https://github.com/<owner>/<repo>/issues/<number>` |

### URL Rules

| Rule | Requirement |
|------|-------------|
| Scheme | Must be `https://` |
| Host | Must be `github.com` |
| Path | Must match `/owner/repo/issues/number` |
| No `github://` fallback | **Forbidden.** The `github://issues/{issue_id}` fallback must never be used |
| No `urn:` placeholders | Forbidden |
| No API URLs as `source_url` | `https://api.github.com/repos/...` is not a canonical item URL |
| No missing `source_url` | Forbidden |
| No guessed URL without source data | Forbidden |
| Missing or malformed `html_url` → | **Drop** record + report in `missing_url_count` |

### URL Validation

If `html_url` is missing:
- **Reject before pilot run**
- **Do not include in founder review package**
- Count in `missing_url_count` in source quality report

---

## 12. GitHub-Specific Quality Flags

Every GitHub evidence item must carry appropriate quality flags:

| Flag | Trigger | Action |
|------|---------|--------|
| `bot_generated` | User login matches bot patterns (ends with `[bot]`, contains `dependabot`, `renovate`, `stale`, `github-actions`, `codecov`) | Retain with flag; deprioritize |
| `stale_issue` | No `updated_at` within 365 days AND `state == "open"` | Retain with flag; deprioritize |
| `low_text_context` | Body < 200 chars AND no reproduction steps or impact | Retain with flag; deprioritize |
| `maintainer_housekeeping` | Title matches housekeeping patterns (`chore:`, `build:`, `ci:`, `bump`, `release`) | Retain with flag; usually exclude from review |
| `duplicate_or_invalid` | Labels contain `duplicate`, `invalid` | Retain with flag; exclude unless new pain detail |
| `wontfix_or_not_planned` | `state_reason == "not_planned"` or label `wontfix` | Retain with flag; include only if rich pain description |
| `source_access_limited` | Rate limit hit, incomplete results, or pagination truncated | Set if collection was interrupted |
| `requires_manual_review` | Classification uncertain; needs human judgment | Retain; flag for founder attention |
| `integration_pain` | Body contains integration/connector/compatibility pain keywords | Boost relevance |
| `debugging_pain` | Body contains debug/trace/observability pain keywords | Boost relevance |
| `reliability_pain` | Body contains reliability/flaky/timeout/crash keywords | Boost relevance |
| `workflow_pain` | Body contains manual/workaround/automation gap keywords | Boost relevance |
| `locked_issue` | `locked == true` | Retain with flag |
| `closed_stale` | Issue closed > 365 days ago with no recent activity | Flag; include only if pain pattern is recurring |

---

## 13. Noise Risks

| # | Risk | Likelihood | Mitigation |
|---|------|------------|------------|
| R-1 | **GitHub is developer-heavy** | High | Focus themes include non-dev domains (finance, ops); document bias in results report |
| R-2 | **Popular repos overrepresent implementation detail** | High | Per-repo caps limit any single repo's dominance; anti-dominance rule enforced |
| R-3 | **Bot/stale/duplicate noise** | Medium | Quality flags identify these; deprioritize in downstream review |
| R-4 | **Feature requests may be wishlist, not pain** | Medium | Inclusion criteria require pain evidence, not just "add X"; flag wishlist |
| R-5 | **Closed issues may be solved and less useful** | Medium | Prefer open issues; closed issues must carry strong pain evidence |
| R-6 | **Repo selection bias toward AI/devtools** | Medium | Finance/ops repos included (Group E) despite lower issue volume; document underrepresentation |
| R-7 | **Some buyer/ICP signals are indirect** | Medium | GitHub issues show technical pain; downstream opportunity framing must translate to business value |
| R-8 | **Finance/SMB pain may be underrepresented** | Medium-High | Finance/ops repos are a minority of the allowlist; this reflects GitHub's audience skew; complement with HN evidence |
| R-9 | **AI/LLM repos have hype bias** | Medium | Focus on bug/pain keywords over feature requests; label-based filtering helps |
| R-10 | **Large repos may have rate-limit impact on live collection** | Medium | Per-repo caps bound collection volume; fixture-first strategy mitigates |
| R-11 | **`incomplete_results` from Search API** | Low-Medium | If `incomplete_results: true`, flag in source quality summary; records still valid |
| R-12 | **`html_url` may be missing in edge cases** | Low | Hard requirement: drop records without `html_url`; tested explicitly |

---

## 14. Expected GitHub Contribution to Pilot

### Expected GitHub Role

| Can Do | Description |
|--------|-------------|
| Validate technical pain | Confirm unresolved bugs, defects, and workflow gaps from real-world usage |
| Reveal integration/debugging/reliability issues | Surface concrete technical pain with reproduction steps and impact |
| Expose repeated workaround patterns | Find issues where users describe scripts, hacks, manual workarounds |
| Complement HN discussion with concrete issue evidence | Ground community discussion in verifiable issue-tracker data |
| Improve recurrence/source diversity for PainClusters | Add cross-source evidence; strengthen cluster signal |
| Surface ecosystem-level pain | Same pain pattern across multiple repos indicates broad market gap |

### Expected NOT to Do

| Cannot Do | Reason |
|-----------|--------|
| Prove market size | Issue count ≠ market size |
| Prove willingness to pay alone | GitHub complaints ≠ validated buyer intent |
| Represent non-technical SMB finance pain comprehensively | GitHub audience skews technical; finance/SMB underrepresented |
| Replace founder interviews | GitHub is observational, not interventional |
| Replace HN community evidence | Different signal types; complementary |
| Validate buyer identity | Issue reporters are often anonymous or pseudonymous |

---

## 15. GitHub Review Questions for Founder

After GitHub evidence is collected, the founder should answer:

| # | Question | What to Assess |
|---|----------|---------------|
| Q-1 | Which repos produced useful pain? | Repo performance; which repos should stay in Cycle 2 |
| Q-2 | Which repos produced implementation noise? | Repos to kill or deprioritize for Cycle 2 |
| Q-3 | Which repos should be killed from Cycle 2? | Explicit repo retirement decisions |
| Q-4 | Did GitHub evidence strengthen any HN pain cluster? | Cross-source signal reinforcement |
| Q-5 | Are the pains too developer-tooling-specific? | Audience bias assessment; is business relevance clear? |
| Q-6 | Are any issues close to reachable buyer/ICP? | Are issue reporters or affected users in target ICPs? |
| Q-7 | Are there repos missing from the allowlist? | Gaps in repo coverage for Pilot themes |
| Q-8 | Should finance/SMB operational repos be increased or decreased? | Group E sizing decision for Cycle 2 |
| Q-9 | Is the per-repo cap appropriate? | Was 10 per P0 repo too high/too low? |
| Q-10 | Was the GitHub evidence volume sufficient? | 25–75 target assessment; should Cycle 2 target more or less? |

---

## 16. Approval Gate

This plan **does not authorize live GitHub collection**.

| Gate | Requirement |
|------|-------------|
| Live GitHub Issues collection | Founder approval **required** before live GitHub API calls |
| Repo allowlist | Founder approval **required** for final repo allowlist before collection |
| Without live approval | Use manual bounded input or fixture fallback |
| Runtime outputs | Must use explicit `output_dir` |
| Committed repository artifacts | None unless explicitly approved |

### Live Collection Approval Checklist

Before live GitHub Issues collection can proceed, the founder must explicitly:

1. Confirm approval of this query plan.
2. Review and approve the repo allowlist (Section 5).
3. Confirm approval of the first-cycle subset (Section 6).
4. Confirm approval of live GitHub API access.
5. Confirm the `output_dir` for runtime artifacts (must not be a default repository path).
6. Acknowledge that collection caps (max 100 items; per-repo caps) are in effect.
7. Acknowledge that PR filtering is mandatory and non-configurable.
8. Acknowledge that `html_url` traceability is mandatory; items without it are dropped.

---

## 17. Dry-Cycle Fallback

If live GitHub collection is not approved:

| Step | Action |
|------|--------|
| 1 | Manually collect 5–15 GitHub issue URLs from proposed P0 repos |
| 2 | Prepare bounded input JSON manually or via approved process |
| 3 | Preserve `source_id` (`github_issues`), `source_type` (`issue_tracker`), `source_url` (`html_url`) for every item |
| 4 | Exclude PRs |
| 5 | Run pilot on bounded input only |

### Dry-Cycle Minimum Items

| Artifact | Minimum |
|----------|---------|
| GitHub raw evidence items | 5–15 |
| P0 repos covered | At least 5 of 7 P0 repos |
| P0 repos with at least 1 issue | At least 3 |

A dry cycle that produces fewer than 5 GitHub items is not a failure — but requires a documented explanation of why so few items were collected.

---

## 18. Integration with GitHub Issues Connector Hardening Plan

This query plan references the [GitHub Issues Connector Hardening Plan](github_issues_connector_hardening_plan.md) for:

- GitHub issue → `RawEvidence` field mapping (Section 6)
- `evidence_kind` classification heuristics (Section 9)
- `source_url` hardening — removal of `github://` fallback (Section 6.4)
- PR filtering rules (Section 7)
- Comments policy (Section 8)
- Noise and quality filters (Section 12)
- Controlled smoke plan (Section 16)

The hardening plan addresses **implementation-level** concerns (field mapping, classification, deduplication, smoke testing). This query plan addresses **operational** concerns (which repos to query, how many issues to collect, what to accept/reject, what approval gates exist).

Both plans are mutually reinforcing. The query plan defines the repo allowlist and search logic; the hardening plan defines how the adapter processes GitHub data. Neither plan authorizes live collection by itself.

---

## 19. Self-Audit Checklist

- [x] **Title and status present** (header): Title, status, roadmap item, branch, based-on references
- [x] **Purpose stated** (Section 1): Bounded, traceable collection; not broad search; not source expansion; no live authorization
- [x] **Source scope defined** (Section 2): `source_id`, `source_type`, constraints, content types, exclusions
- [x] **Repo selection principles defined** (Section 3): 7 principles for allowlist inclusion
- [x] **Pilot focus themes defined** (Section 4): 7 themes with GitHub relevance assessment
- [x] **Proposed repo allowlist table present** (Section 5): 22 repos across 5 groups (A–E), each row with all required columns (priority, repo, theme, rationale, expected evidence_kind, expected pain patterns, noise risks, per-repo cap, include if, exclude/flag if, verification_required, founder_approval_required)
- [x] **At least 15 candidate repos listed** (Section 5): 22 repos
- [x] **Verification status explicit** (Section 5): All repos marked `verification_required = true`
- [x] **Priority tiers defined**: P0 (first-cycle core), P1 (use if volume needed), P2 (backup/optional)
- [x] **First-cycle recommended subset defined** (Section 6): 10 repos with domain mix percentages
- [x] **Reserve repos listed** (Section 6): 12 reserve repos
- [x] **Collection parameters defined** (Section 7): Volume targets, per-repo caps, time window, issue state policy
- [x] **Issue search logic defined** (Section 8): Common filters, pain keywords, AI/LLM-specific keywords, per-repo query templates, prohibited patterns
- [x] **Inclusion criteria defined** (Section 9): 13 criteria
- [x] **Exclusion/noise criteria defined** (Section 10): 15 noise patterns with actions and handling policy
- [x] **Source URL traceability explicit** (Section 11): URL format, rules, validation policy; `html_url` mandatory; `github://` forbidden
- [x] **PR filtering explicit** (Section 2, Section 8, Section 10): `is:issue` filter + `pull_request` key check; mandatory and non-configurable
- [x] **GitHub-specific quality flags defined** (Section 12): 14 flags with triggers and actions
- [x] **Noise risks documented** (Section 13): 12 risks with likelihood and mitigation
- [x] **Expected GitHub contribution defined** (Section 14): Can do / cannot do split
- [x] **Founder review questions defined** (Section 15): 10 questions
- [x] **Approval gates explicit** (Section 16): Live collection requires founder approval; 8-item checklist
- [x] **Dry-cycle fallback defined** (Section 17): 5–15 manual issue URLs; minimum P0 repo coverage
- [x] **Integration with hardening plan** (Section 18): Mutual reinforcement noted
- [x] **No implementation directives**: Document is operational planning only
- [x] **No live API authorization**: Explicit approval gate preserved
- [x] **No source code, test, script, or artifact modifications**
- [x] **No live GitHub queries executed**

---

## 20. Definition of Done

Item 4 is done when:

- [x] **4.1** GitHub repo allowlist/query plan exists at `docs/decisions/github_issues_repo_allowlist_query_plan_v2_13.md`
- [x] **4.2** Proposed repo allowlist is documented: 22 repos across 5 groups (A–E)
- [x] **4.3** At least 15 candidate repos are listed: 22 repos
- [x] **4.4** First-cycle recommended subset is defined: 10 repos with domain mix
- [x] **4.5** Collection caps are defined: 25–75 target; max 100; per-repo caps by tier
- [x] **4.6** Issue search logic is defined: templates, keywords, prohibited patterns
- [x] **4.7** Inclusion criteria are defined: 13 criteria
- [x] **4.8** Exclusion/noise criteria are defined: 15 noise patterns with handling policy
- [x] **4.9** Source URL policy is explicit: `html_url` mandatory; `github://` forbidden; drop on missing
- [x] **4.10** PR filtering is explicit: mandatory, non-configurable, `is:issue` + `pull_request` key check
- [x] **4.11** Approval gates are explicit: founder approval required for live collection and repo allowlist
- [x] **4.12** Dry fallback is defined: 5–15 manual issue URLs; minimum P0 coverage
- [x] **4.13** GitHub review questions for founder defined: 10 questions
- [x] **4.14** Quality flags defined: 14 GitHub-specific flags
- [x] **4.15** Noise risks documented: 12 risks
- [ ] **4.16** `.\scripts\dev-git-check.ps1` passes
- [ ] **4.17** One local commit exists with message: `[v2.13] 4 define github issues query plan`

---

*GitHub Issues Repo Allowlist and Query Plan v2.13. Operational planning document. Does not authorize live collection. Does not modify source code, tests, scripts, or pipeline behavior.*
