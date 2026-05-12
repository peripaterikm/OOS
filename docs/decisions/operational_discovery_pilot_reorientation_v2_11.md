# Operational Discovery Pilot Reorientation v2.11

**Title:** Operational Discovery Pilot Reorientation v2.11
**Status:** Approved strategy correction / implementation pending
**Roadmap:** v2.11
**Decision date:** 2026-05-12

---

## 1. Context

v2.11 started as *Discovery Sources and Market Scout Foundation*. The original plan called for:

1. Defining source adapter contracts, schemas, and registry (items 1–3)
2. Hardening plans for HN and GitHub Issues (items 4–5)
3. Feasibility plans for Product Hunt and pimenov.ai (items 6–7)
4. Source quality scoring and weekly reporting contracts (items 8–9)
5. A final planning checkpoint (item 10)

Items 1–6 are complete. They created useful source contracts, schemas, and feasibility plans that remain valid references.

However, continuing to expand sources (pimenov.ai, Product Hunt, Reddit, AlternativeTo, YC, marketplaces, job boards, Discord/Slack/X, newsletters, blogs) before running an operational pilot on the sources already available creates a risk: **building a large ingestion machine without proving the system finds useful business pains, rather than merely classifying noise.**

More sources do not equal better opportunities. The system must first demonstrate that it can find meaningful pains from a limited, well-understood source set, convert them into pain clusters, form opportunity candidates, and support founder decisions — all before scaling the ingestion surface.

---

## 2. Core Decision

**Stop source expansion now.**

v2.11 is re-scoped into an **Operational Discovery Pilot** with the following constraints:

| Decision | Detail |
|----------|--------|
| **Primary sources** | HN + GitHub Issues |
| **Stretch source (optional)** | Stack Exchange / Stack Overflow |
| **Deferred** | Product Hunt, pimenov.ai, Reddit, AlternativeTo, YC, marketplaces, job boards, Discord/Slack/X, blogs/newsletters |
| **pimenov.ai treatment** | Deferred to a later context/intelligence layer; it is an expert/context source, not a direct pain source |
| **Product Hunt treatment** | Feasibility plan preserved as future reference; not included in the operational pilot; it is a solution-pattern/product-launch source, not a direct pain source |

---

## 3. Why This Change Is Needed

1. **More sources != better opportunities.** Without proof that the current pipeline extracts useful business pains, adding sources multiplies noise, not signal.
2. **The system must prove it can find useful pains.** OOS has a deterministic processing pipeline but has not yet been validated end-to-end against real, open-web sources in an operational cadence.
3. **Scoring, clustering, founder review, and weekly reporting need real-world testing.** Contracts and plans exist, but the operational feedback loop has not been exercised.
4. **Without pilot feedback, adding sources risks multiplying noise.** Each source has its own idioms, noise patterns, and failure modes. Adding them in parallel before understanding the base signal quality of the current set would overwhelm founder review.

---

## 4. Pilot Objectives

The operational pilot must answer these questions:

1. **What pains are actually found?** Are the extracted signals real, specific, and actionable pains, or are they mostly complaints, announcements, and noise?
2. **Which signals become opportunity candidates?** Do accepted signals cluster into coherent problems that could form the basis of a business hypothesis?
3. **Does scoring work?** Does the pain-first scoring formula (Section 8) produce rankings that match founder intuition?
4. **Is founder review useful?** Do the PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER decisions lead to better signals over time?
5. **Which sources generate noise?** Per-source quality assessment: does one source dominate noise while another yields high-signal material?
6. **Do 1–2 ideas emerge that are worth validating?** The ultimate test: can the pilot surface at least one or two business hypotheses worth testing via interview, landing page, or manual research?

---

## 5. Pilot Source Scope

### 5.1 Hacker News (Primary)

- **Role:** Community pain + early solution discussion
- **Useful areas:** Ask HN, Show HN, Launch HN, comments
- **Current status:** Already partially present in OOS via [`hn_algolia_collector.py`](src/oos/hn_algolia_collector.py)
- **Hardening plan:** [`docs/decisions/hacker_news_connector_hardening_plan.md`](docs/decisions/hacker_news_connector_hardening_plan.md)

### 5.2 GitHub Issues (Primary)

- **Role:** Technical pain + unresolved devtools/AI/data issues
- **Must use:** repo allowlist (configured in [`config/source_registry.json`](config/source_registry.json))
- **Must filter:** pull requests (PRs are not issues)
- **Current status:** Already present in OOS via [`github_issues_collector.py`](src/oos/github_issues_collector.py)
- **Hardening plan:** [`docs/decisions/github_issues_connector_hardening_plan.md`](docs/decisions/github_issues_connector_hardening_plan.md)

### 5.3 Stack Exchange / Stack Overflow (Optional / Stretch)

- **Role:** Recurring "how do I" pain; technical friction
- **Access method:** Official Stack Exchange API
- **Inclusion rule:** Include only if it does not slow the pilot cadence
- **Default:** Do not include in the first pilot run; reassess after 1–2 weekly cycles

---

## 6. Explicitly Deferred Sources

The following sources are explicitly deferred to v2.14+ (post-pilot source expansion phase) unless separately approved by the founder:

| Source | Reason for deferral |
|--------|---------------------|
| Reddit | API volatility, high noise, moderation complexity |
| Discord | No stable public API; scraping risk |
| Slack | No public API for community content; workspace access barriers |
| X/Twitter | API cost/restrictions; legal review required |
| Product Hunt | Solution-pattern source, not direct pain source; feasibility plan preserved as reference |
| AlternativeTo | Review-based; signal-type fit unclear |
| YC RFS / YC companies | Curated lists; not a structured pain feed |
| Crunchbase | Company data, not pain signals |
| Blogs / newsletters | Ingest pipeline complexity; copyright considerations |
| pimenov.ai | Expert/context source, not direct pain source; deferred to context/intelligence layer |
| App marketplaces (Google Play, App Store) | Review-based; scraping risk |
| Job boards (LinkedIn, Indeed) | ToS barriers; scraping risk |

All deferred sources remain in the v2.12+ hooks table in the roadmap. None may be implemented before the pilot completes and a Go decision is made (v2.13).

---

## 7. PainCluster: First-Class Pilot Artifact

**PainCluster** is defined as a first-class pilot artifact. A PainCluster represents the same pain observed across multiple sources, with multiple evidence points, consolidated into one cluster — not multiple separate ideas.

### 7.1 Minimum Fields

| Field | Type | Description |
|-------|------|-------------|
| `cluster_id` | string | Stable identifier for the cluster |
| `actor` | string | Who experiences the pain (role, persona) |
| `workflow` | string | The task or workflow being disrupted |
| `object` | string | The tool, system, or process causing the pain |
| `pain_verb` / `pain_pattern` | string | The specific pain action or recurring pattern (e.g., "cannot integrate", "loses data", "manual workaround required") |
| `source_evidence_list` | list[source_url] | All raw evidence URLs supporting this cluster |
| `source_diversity` | int | Count of distinct source types (e.g., HN + GitHub Issues = 2) |
| `recurrence` | int | Number of distinct evidence items expressing this pain |
| `business_relevance` | float | 0.0–1.0 estimate of whether this pain could support a business |
| `noise_risk` | float | 0.0–1.0 estimate that this cluster is noise, not real pain |
| `representative_quotes` | list[string] | Short excerpts (≤200 chars each) that capture the pain in the user's own words |
| `linked_candidate_signals` | list[signal_id] | Candidate signals feeding this cluster |
| `linked_opportunity_candidates` | list[opportunity_id] | Opportunity candidates formed from this cluster |

### 7.2 Clustering Rule

Same pain observed across HN, GitHub Issues, and Stack Overflow **must become one pain cluster with multiple evidence points**, not three separate ideas. Cross-source consolidation is mandatory.

---

## 8. Explicit Scoring Formula

The initial pain-first scoring formula for candidate signals:

```
overall =
    0.25 * pain_explicitness
  + 0.20 * recurrence
  + 0.15 * business_cost
  + 0.15 * icp_fit
  + 0.10 * source_reliability
  + 0.10 * freshness
  + 0.05 * actionability
  - 0.20 * noise_risk
```

### 8.1 Component Definitions

| Component | Range | Definition |
|-----------|-------|------------|
| `pain_explicitness` | 0.0–1.0 | How explicitly the source describes a real pain (specific, concrete, attributable to an actor) vs a vague complaint or announcement |
| `recurrence` | 0.0–1.0 | How many distinct evidence items express the same or similar pain; normalized across the pilot batch |
| `business_cost` | 0.0–1.0 | Estimated cost of the pain to the actor: time lost, money spent, opportunity cost, operational drag |
| `icp_fit` | 0.0–1.0 | How well the pain matches the founder's Ideal Customer Profile and domain preferences |
| `source_reliability` | 0.0–1.0 | Historical signal quality of the source (HN: moderate; GitHub Issues: moderate-high when allowlisted) |
| `freshness` | 0.0–1.0 | Recency of the evidence; decays with age |
| `actionability` | 0.0–1.0 | Can a product or service realistically address this pain? Is there a plausible solution? |
| `noise_risk` | 0.0–1.0 | Estimated probability this is noise: off-topic, promotional, banal, trolling, or unactionable |

### 8.2 Weight Policy

Weights are **pilot defaults** and may be tuned in v2.12 based on pilot results. The formula is deterministic (no LLM required for scoring). All components must be explainable from the evidence.

---

## 9. Source Quality Report Requirement

Each pilot run must produce a **Source Quality Report** covering:

| Section | Content |
|---------|---------|
| Raw evidence collected | Count, source breakdown, time range |
| Accepted / weak / noise signals | Signal classification breakdown per source |
| Top pain clusters | Ranked list with scores, recurrence, cross-source diversity |
| Opportunity candidates formed | List with linked clusters, scores, founder review status |
| Source quality by source | Per-source: signal rate, noise rate, missing coverage, traceability gaps |
| Main noise categories | What patterns dominated the noise (e.g., "launch announcements", "hiring posts", "vague complaints") |
| Founder decisions needed | List of signals/clusters/opportunities awaiting PROMOTE/PARK/KILL/NEEDS_MORE_EVIDENCE/REVISIT_LATER |
| Next validation actions | Recommended next steps (interview targets, landing page tests, manual research directions) |

---

## 10. Founder Review Loop

Founder review is mandatory. Each signal, cluster, and opportunity candidate must receive one of these statuses:

| Status | Meaning |
|--------|---------|
| `PROMOTE` | Move forward: signal accepted, cluster confirmed, opportunity candidate worth validating |
| `PARK` | Interesting but not now; move to parking lot for revisit |
| `KILL` | Not useful; document `KillReason` explaining why the idea died, not just a label |
| `NEEDS_MORE_EVIDENCE` | Plausible but insufficient; request additional evidence collection |
| `REVISIT_LATER` | Possibly relevant in the future; set revisit trigger |

Founder decisions must feed back into scoring and filtering: patterns in KILL decisions must inform noise_risk calibration; patterns in PROMOTE decisions must inform icp_fit tuning.

---

## 11. Pilot Success Criteria

A **good result** after 1–2 weekly cycles:

| Metric | Expected Range |
|--------|---------------|
| Raw evidence items | 50–150 |
| Candidate signals | 10–30 |
| Pain clusters | 3–7 |
| Opportunity candidates | 3–5 |
| Ideas worth validation | At least 1–2 (via interview, landing page, or manual research) |
| Traceability | Every candidate has traceability to `source_url` / evidence |

Success means the pipeline surfaces *real, specific business pains* that a founder would seriously consider validating. It does not mean "produces many signals" — it means "produces signals worth acting on."

---

## 12. Pilot Failure Criteria

A **bad result**:

- 90%+ of raw evidence is classified as noise
- Candidate signals are banal ("people want faster software", "AI is changing everything")
- Opportunity candidates are abstract and unactionable ("an AI-powered platform for developers")
- Founder review becomes manual trash sorting with no learning feedback
- Weekly review looks smart on paper but does not support actual decisions

If the pilot fails, the Go/No-Go decision (v2.13) must recommend either:
- Fix the pipeline with specific, targeted improvements; OR
- Reconsider whether open-web pain discovery is the right top-of-funnel for OOS.

---

## 13. Updated Development Order

| Version | Phase | Description |
|---------|-------|-------------|
| **v2.11** | Operational Discovery Pilot | Run pilot on HN + GitHub Issues; produce PainClusters, opportunity candidates, source quality reports, and founder review decisions |
| **v2.12** | Pilot Quality Improvements | Tune scoring weights; fix noise filters; adjust source configuration based on pilot data; add Stack Exchange if beneficial |
| **v2.13** | Go/No-Go Decision | Evaluate pilot results against success/failure criteria; decide whether to expand sources in v2.14+ or pivot |
| **v2.14+** | Source Expansion (conditional) | Only if pilot passes Go decision: add Product Hunt, Reddit, and other deferred sources per prioritized feasibility assessments |

---

## 14. Non-Goals

The following are explicitly excluded from v2.11 under the reoriented scope:

- Adding more sources now (any source outside HN + GitHub Issues + optional Stack Exchange)
- Implementing Product Hunt now (plan preserved as reference)
- Implementing pimenov.ai now (deferred to context layer)
- Broad scraping of any kind
- Social media sources (Reddit, Discord, Slack, X/Twitter)
- Marketplaces (Google Play, App Store, etc.)
- Job boards (LinkedIn, Indeed, etc.)
- Blogs/newsletters
- Replacing founder review with automation
- Live API calls in unit tests
- LLM-based validation in default tests
- Database or persistent server architecture
- UI/dashboard work

---

## 15. Decision

**v2.11 is reoriented from "Discovery Sources and Market Scout Foundation" to "Operational Discovery Pilot."**

- Source expansion stops now.
- The pilot runs on HN + GitHub Issues (primary) with Stack Exchange / Stack Overflow as optional stretch.
- Previous source feasibility documents (Product Hunt, pimenov.ai, HN hardening, GitHub hardening) remain useful references for future source expansion post-pilot.
- No new source implementation starts before the pilot completes and a Go decision is made in v2.13.
- pimenov.ai is classified as an expert/context source, not a direct pain source, and is deferred to a later context/intelligence layer.
- Product Hunt is classified as a solution-pattern/product-launch source, not a direct pain source, and is deferred to v2.14+.
