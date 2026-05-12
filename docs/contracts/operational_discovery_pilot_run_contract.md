# Operational Discovery Pilot Run and Source Quality Report Contract

**Version:** operational_discovery_pilot_run_contract.v1
**Roadmap:** v2.11
**Item:** 9
**Status:** Contract finalized / implementation pending
**Depends on:**
- [`operational_discovery_pilot_reorientation_v2_11.md`](../decisions/operational_discovery_pilot_reorientation_v2_11.md) (v2.11 item 7)
- [`pain_cluster_contract.md`](pain_cluster_contract.md) (v2.11 item 8)
- [`discovery_source_adapter_contract.md`](discovery_source_adapter_contract.md) (v2.11 item 1)
- [`raw_evidence_artifact_schema.md`](raw_evidence_artifact_schema.md) (v2.11 item 2)
- [`source_allowlist_policy.md`](source_allowlist_policy.md) (v2.11 item 3)
- [`source_url_traceability_contract.md`](source_url_traceability_contract.md) (v2.7 item 1.1)
- [`hacker_news_connector_hardening_plan.md`](../decisions/hacker_news_connector_hardening_plan.md) (v2.11 item 4)
- [`github_issues_connector_hardening_plan.md`](../decisions/github_issues_connector_hardening_plan.md) (v2.11 item 5)
**Precedes:**
- Roadmap v2.11 item 10 — Final v2.11 Pilot Planning Checkpoint
- Roadmap v2.12 — Pilot Quality Improvements (scoring weight tuning, noise filter fixes)
- Roadmap v2.13 — Go/No-Go Decision

---

## 1. Title and Status

**Title:** Operational Discovery Pilot Run and Source Quality Report Contract
**Roadmap:** v2.11
**Item:** 9
**Status:** Contract finalized / implementation pending

This document defines the combined contract for:
1. The **Operational Discovery Pilot Run** — the end-to-end design of how the pilot collects evidence, processes signals, forms pain clusters, generates opportunity candidates, and routes to founder review on a weekly cadence.
2. The **Source Quality Report** — the structured report that gates each pilot run, measuring source quality, noise rates, cluster quality, and founder decision impact.

No implementation is authorized by this contract. No runtime behavior is changed. No artifacts are generated.

---

## 2. Context

### 2.1 Why This Pilot Exists

v2.11 is reoriented into an **Operational Discovery Pilot** (see [`operational_discovery_pilot_reorientation_v2_11.md`](../decisions/operational_discovery_pilot_reorientation_v2_11.md)). The original scope — expanding sources to Product Hunt, pimenov.ai, Reddit, and beyond — is deferred. Instead, the system must first prove it finds useful business pains from a limited, well-understood source set before scaling the ingestion surface.

The purpose of the pilot is **not** to prove that OOS can ingest many sources. It is to prove that OOS can produce useful founder decisions.

### 2.2 Pilot Source Scope

| Source | Role | Status |
|--------|------|--------|
| **Hacker News** | Community pain + early solution discussion. Ask HN, Show HN, relevant comments prioritized. | Primary |
| **GitHub Issues** | Technical pain + unresolved devtools/AI/data issues. Repo allowlist required. PR filtering mandatory. | Primary |
| **Stack Exchange / Stack Overflow** | Recurring "how do I" pain; technical friction. Official API only. | Optional / stretch — include only if it does not slow the pilot cadence. Default: excluded from first 1–2 weekly cycles. |

### 2.3 Deferred Sources

All sources beyond HN + GitHub Issues (+ optional Stack Exchange) are deferred to v2.14+, conditional on a Go decision in v2.13. See Section 5 for the complete exclusion list.

---

## 3. Pilot Objective

The operational pilot must answer these questions:

1. **What pains are actually found?** Are the extracted signals real, specific, and actionable business pains, or are they mostly complaints, announcements, and noise?
2. **Which signals become opportunity candidates?** Do accepted signals cluster into coherent problems that could form the basis of a business hypothesis?
3. **Does scoring work?** Does the pain-first scoring formula from [`pain_cluster_contract.md`](pain_cluster_contract.md) produce rankings that match founder intuition?
4. **Is founder review useful?** Do the PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER decisions lead to better signals over time?
5. **Which sources generate noise?** Per-source quality assessment: does one source dominate noise while another yields high-signal material?
6. **Do 1–2 ideas emerge that are worth validating?** The ultimate test: can the pilot surface at least one or two business hypotheses worth testing via interview, landing page, or manual research?

The pilot objective is achieved when the following operational steps are completed:

- collect limited raw evidence;
- normalize candidate signals;
- form pain clusters;
- generate opportunity candidates;
- produce source quality report;
- route candidates/clusters to founder review;
- collect founder feedback;
- evaluate Go/No-Go for source expansion.

---

## 4. Pilot Scope

The pilot includes these activities:

| # | Activity | Description |
|---|----------|-------------|
| 1 | **HN collection** | Fixture-based or bounded live-opt-in evidence collection from Hacker News via Algolia Search API. Prioritize Ask HN, Show HN, and relevant comment threads. |
| 2 | **GitHub Issues collection** | Fixture-based or bounded live-opt-in evidence collection from GitHub Issues via REST API. Must use repo allowlist from [`config/source_registry.json`](../../config/source_registry.json). Must filter pull requests. |
| 3 | **Stack Exchange (optional stretch)** | If included: official API only. Do not include if it slows the pilot cadence. |
| 4 | **Cross-source deduplication** | Same pain observed across HN + GitHub Issues must become one cluster, not multiple duplicate ideas. |
| 5 | **PainCluster generation** | Produce PainCluster artifacts per [`pain_cluster_contract.md`](pain_cluster_contract.md). |
| 6 | **PainCluster scoring** | Apply the deterministic scoring formula from [`pain_cluster_contract.md`](pain_cluster_contract.md) Section 11. |
| 7 | **Source quality reporting** | Produce a structured Source Quality Report (this contract) for each pilot run. |
| 8 | **Founder review loop** | Route clusters and opportunity candidates to founder review with PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER statuses. |
| 9 | **Weekly pilot report** | Produce a human-readable weekly pilot report summarizing findings and decisions. |

---

## 5. Explicit Non-Scope

The following sources and activities are explicitly excluded from the pilot. They must not be implemented, connected, or fetched during the pilot run:

| Excluded | Reason |
|----------|--------|
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

Also excluded from the pilot:
- Broad scraping of any kind
- Live APIs in unit tests
- LLM validation in default tests
- Automatic founder decisions (founder review is mandatory)
- UI/dashboard work
- Database or persistent server architecture
- Implementation in this item (this is a contract only)

---

## 6. Pilot Run Inputs

A pilot run accepts the following inputs:

| Input | Type | Description | Required |
|-------|------|-------------|----------|
| Source registry | Configuration | [`config/source_registry.json`](../../config/source_registry.json) with active pilot sources | Yes |
| HN fixture or live-opt-in | Fixture file or API opt-in | HN evidence via Algolia API or deterministic fixture | Yes (one of) |
| GitHub Issues fixture or live-opt-in | Fixture file or API opt-in | GitHub Issues evidence via REST API or deterministic fixture | Yes (one of) |
| Stack Exchange fixture or live-opt-in | Fixture file or API opt-in | Stack Exchange evidence via official API or deterministic fixture | No (stretch) |
| Source allowlist | Configuration | Allowlist policy gates per [`source_allowlist_policy.md`](source_allowlist_policy.md) | Yes |
| Repo allowlist | Configuration | List of approved GitHub repos for issue collection | Yes |
| Query allowlist | Configuration | Approved search queries for each source | Yes |
| Scoring configuration | Configuration | Scoring weights and thresholds from [`pain_cluster_contract.md`](pain_cluster_contract.md) | Yes |
| Founder ICP / preferences | Configuration (optional) | Ideal Customer Profile and domain preferences for `icp_fit` scoring | No |

**Fixture mode** (default for tests): All inputs come from deterministic fixture files. No network calls.

**Live mode** (opt-in only): Inputs come from live API calls. Requires explicit founder approval. Never enabled in unit tests.

---

## 7. Pilot Run Outputs

Each pilot run must produce the following outputs:

| # | Output | Type | Description |
|---|--------|------|-------------|
| 1 | Raw evidence artifacts | JSON files | Normalized [`RawEvidence`](../../src/oos/models.py:77) records per source |
| 2 | Candidate signals | JSON file | Extracted [`CandidateSignal`](../../src/oos/models.py:228) objects |
| 3 | Weak / noise buckets | JSON file | Signals classified as weak or noise, with classification reasons |
| 4 | Pain clusters | JSON file | PainCluster artifacts per [`pain_cluster_contract.md`](pain_cluster_contract.md) |
| 5 | Opportunity candidates | JSON file | Opportunity candidates framed from top-scoring pain clusters |
| 6 | Source quality report | JSON + Markdown | Structured quality report per this contract (Section 10) |
| 7 | Founder review package | JSON file | Package of clusters and opportunity candidates awaiting founder decisions |
| 8 | Weekly pilot report | Markdown | Human-readable weekly summary (Section 15) |
| 9 | Validation summary | JSON file | Pass/fail/warn results for all validation rules |
| 10 | Traceability index | JSON file | Index mapping every candidate back to `source_url` evidence |

Every output must satisfy [`source_url_traceability_contract.md`](source_url_traceability_contract.md): no placeholder URLs, no `urn:oos:*` URNs. Every candidate has traceability to a real source URL.

---

## 8. Proposed Artifact Locations

The following paths are proposed for pilot run artifacts. These are contract-level path conventions for later implementation. **No artifacts are created now.**

```
artifacts/discovery/pilot_runs/<run_id>/
├── raw_evidence/
│   ├── hacker_news_algolia.json
│   ├── github_issues.json
│   └── stack_exchange.json                  (optional; stretch source only)
├── candidate_signals.json
├── weak_noise_buckets.json
├── pain_clusters.json
├── opportunity_candidates.json
├── source_quality_report.json
├── source_quality_report.md
├── founder_review_package.json
├── weekly_pilot_report.md
├── traceability_index.json
└── validation_summary.json
```

Run ID format: `pilot_run_YYYY-MM-DD_<8char_hex>` (e.g., `pilot_run_2026-05-12_a1b2c3d4`).

All paths are relative to the repository root. The `artifacts/` directory is `.gitignore`'d per standard OOS policy. Artifact paths are advisory; implementation may adjust as long as all required outputs are produced.

---

## 9. Pilot Run Lifecycle

Each pilot run proceeds through these phases in order:

| Phase | Name | Description | Produces |
|-------|------|-------------|----------|
| 1 | **Preflight** | Validate configuration: source registry, allowlists, fixture presence, scoring config. Reject run if preflight fails. | Preflight pass/fail log |
| 2 | **Source collection / fixture loading** | Fetch evidence from live APIs (opt-in) or load from deterministic fixtures (default). One adapter call per source. | `raw_evidence/*.json` |
| 3 | **Raw evidence validation** | Validate every `RawEvidence` record: `source_url` present and valid, required fields populated, UTF-8 encoding correct. Reject invalid records. | Validation errors/warnings log |
| 4 | **Candidate signal extraction** | Extract [`CandidateSignal`](../../src/oos/models.py:228) objects from validated raw evidence. Classify each signal: accepted, weak, or noise. | `candidate_signals.json`, `weak_noise_buckets.json` |
| 5 | **Weak/noise classification** | Apply noise categories from [`pain_cluster_contract.md`](pain_cluster_contract.md) Section 10. Record classification reason for each weak/noise signal. | Updated `weak_noise_buckets.json` |
| 6 | **Cross-source deduplication** | Detect and merge near-duplicate signals across sources. Same pain from HN + GitHub Issues must become one candidate, not two. | Dedup log; updated `candidate_signals.json` |
| 7 | **PainCluster generation** | Group accepted candidate signals by pain pattern. Form PainCluster artifacts per [`pain_cluster_contract.md`](pain_cluster_contract.md). | `pain_clusters.json` |
| 8 | **PainCluster scoring** | Apply deterministic scoring formula to each cluster. Compute all 8 components. Assign auto-statuses (new, weak, noise). | Updated `pain_clusters.json` with scores |
| 9 | **Opportunity candidate framing** | For clusters scoring `overall >= 0.70` and passing all promotion gates, frame opportunity candidates with problem statement, evidence summary, and suggested validation actions. | `opportunity_candidates.json` |
| 10 | **Source quality reporting** | Compute all source quality metrics (Section 11). Produce structured source quality report (Section 10). | `source_quality_report.json`, `source_quality_report.md` |
| 11 | **Founder review package generation** | Bundle clusters and opportunity candidates into a review package with clear decision prompts. | `founder_review_package.json` |
| 12 | **Weekly pilot report generation** | Produce human-readable weekly pilot report (Section 15). | `weekly_pilot_report.md` |
| 13 | **Founder feedback ingestion** | After founder review, ingest PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER decisions. Feed back into scoring calibration and source quality priors. | Updated scoring configuration; updated source reliability priors |
| 14 | **Pilot retrospective** | After 1–2 weekly cycles: evaluate pilot outcomes against success/failure criteria (Section 16–17). Produce retrospective (Section 23). Inform Go/No-Go (Section 18). | Retrospective summary |

Phases 1–12 run each weekly cycle. Phases 13–14 run after founder feedback is received and at pilot conclusion.

---

## 10. Source Quality Report Structure

Each pilot run must produce a Source Quality Report in both JSON (machine-readable) and Markdown (human-readable) formats.

### 10.1 Required Report Sections

| Section | Content |
|---------|---------|
| **Raw evidence collected** | Total count, per-source breakdown, time range, collection method (fixture/live) |
| **Accepted / weak / noise signals** | Signal classification breakdown: accepted count, weak count, noise count, per-source breakdown |
| **Top pain clusters** | Ranked list of pain clusters with cluster_id, pain_pattern, overall score, recurrence, source_diversity, status |
| **Opportunity candidates formed** | List of opportunity candidates with opportunity_id, linked cluster, problem statement, score, founder review status |
| **Source quality by source** | Per-source: signal rate (accepted/total), noise rate (noise/total), missing coverage areas, traceability gaps, URL validity |
| **Main noise categories** | Dominant noise patterns observed (e.g., "flamewar", "self_promotion", "vague_complaint", "launch_hype", "stale_abandoned") per [`pain_cluster_contract.md`](pain_cluster_contract.md) Section 10.2 |
| **Founder decisions needed** | Count of clusters and opportunity candidates awaiting PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER |
| **Next validation actions** | Recommended next steps: interview targets, landing page test directions, manual research areas, additional evidence needed |

### 10.2 JSON Schema Sketch

```json
{
  "artifact_type": "source_quality_report",
  "schema_version": "1.0.0",
  "pilot_run_id": "pilot_run_2026-05-12_a1b2c3d4",
  "created_at": "2026-05-12T10:00:00Z",
  "metadata": {
    "collection_mode": "fixture",
    "sources_active": ["hacker_news_algolia", "github_issues"],
    "sources_stretch": [],
    "collection_window_start": "2026-05-05T00:00:00Z",
    "collection_window_end": "2026-05-12T00:00:00Z"
  },
  "raw_evidence_summary": {
    "total_records": 85,
    "by_source": {
      "hacker_news_algolia": { "records_seen": 50, "records_emitted": 45, "records_rejected": 5 },
      "github_issues": { "records_seen": 40, "records_emitted": 35, "records_rejected": 5 }
    }
  },
  "signal_classification": {
    "accepted_count": 18,
    "weak_count": 8,
    "noise_count": 14,
    "by_source": {
      "hacker_news_algolia": { "accepted": 10, "weak": 5, "noise": 10 },
      "github_issues": { "accepted": 8, "weak": 3, "noise": 4 }
    }
  },
  "top_pain_clusters": [],
  "opportunity_candidates": [],
  "source_quality_by_source": {
    "hacker_news_algolia": {
      "signal_rate": 0.40,
      "noise_rate": 0.40,
      "weak_rate": 0.20,
      "missing_url_count": 0,
      "placeholder_url_count": 0,
      "source_url_validation_passed": true,
      "main_noise_categories": ["launch_hype", "vague_complaint"]
    },
    "github_issues": {
      "signal_rate": 0.44,
      "noise_rate": 0.22,
      "weak_rate": 0.33,
      "missing_url_count": 0,
      "placeholder_url_count": 0,
      "source_url_validation_passed": true,
      "main_noise_categories": ["low_context_issue", "stale_abandoned"]
    }
  },
  "main_noise_categories": [
    { "category": "launch_hype", "count": 6, "source": "hacker_news_algolia" },
    { "category": "vague_complaint", "count": 4, "source": "hacker_news_algolia" },
    { "category": "low_context_issue", "count": 3, "source": "github_issues" },
    { "category": "stale_abandoned", "count": 2, "source": "github_issues" }
  ],
  "founder_decisions_needed": {
    "clusters_awaiting_review": 5,
    "opportunity_candidates_awaiting_review": 3,
    "total_pending_decisions": 8
  },
  "next_validation_actions": [],
  "traceability_summary": {
    "total_source_urls": 85,
    "missing_url_count": 0,
    "placeholder_url_count": 0,
    "source_url_validation_passed": true
  }
}
```

---

## 11. Source Quality Metrics

The following metrics must be computed for each source and for the pilot run as a whole:

| # | Metric | Type | Description |
|---|--------|------|-------------|
| 1 | `records_seen` | int | Total raw evidence items fetched or loaded from the source |
| 2 | `records_emitted` | int | Items successfully converted to `RawEvidence` |
| 3 | `records_rejected` | int | Items rejected due to validation failure, missing URL, or schema mismatch |
| 4 | `accepted_signal_count` | int | Candidate signals classified as accepted from this source |
| 5 | `weak_signal_count` | int | Candidate signals classified as weak from this source |
| 6 | `noise_signal_count` | int | Candidate signals classified as noise from this source |
| 7 | `accepted_rate` | float | `accepted_signal_count / records_emitted` (0.0–1.0) |
| 8 | `noise_rate` | float | `noise_signal_count / records_emitted` (0.0–1.0) |
| 9 | `duplicate_count` | int | Near-duplicate evidence items detected and merged |
| 10 | `missing_url_count` | int | Evidence items with missing or empty `source_url` |
| 11 | `placeholder_url_count` | int | Evidence items with placeholder URLs (`urn:oos:*` or similar) |
| 12 | `source_url_validation_passed` | bool | True if zero missing and zero placeholder URLs |
| 13 | `source_diversity_contribution` | int | Number of distinct pain clusters this source contributed evidence to |
| 14 | `cluster_contribution_count` | int | Number of pain clusters containing evidence from this source |
| 15 | `opportunity_contribution_count` | int | Number of opportunity candidates linked to clusters containing this source's evidence |
| 16 | `founder_promote_count` | int | Clusters/opportunities from this source that received PROMOTE from founder |
| 17 | `founder_kill_count` | int | Clusters/opportunities from this source that received KILL from founder |
| 18 | `founder_needs_more_evidence_count` | int | Clusters/opportunities from this source that received NEEDS_MORE_EVIDENCE from founder |

These metrics feed the source quality report (Section 10) and inform source reliability prior tuning in v2.12.

---

## 12. PainCluster Reporting

### 12.1 Report Fields per Cluster

For each PainCluster surfaced in the pilot run report, the following fields must be present:

| # | Field | Source |
|---|-------|--------|
| 1 | `cluster_id` | From [`pain_cluster_contract.md`](pain_cluster_contract.md) Section 3.2.1 |
| 2 | `actor` | From [`pain_cluster_contract.md`](pain_cluster_contract.md) Section 3.2.2 |
| 3 | `workflow` | From [`pain_cluster_contract.md`](pain_cluster_contract.md) Section 3.2.3 |
| 4 | `object` | From [`pain_cluster_contract.md`](pain_cluster_contract.md) Section 3.2.4 |
| 5 | `pain_pattern` | From [`pain_cluster_contract.md`](pain_cluster_contract.md) Section 3.2.6 |
| 6 | `overall_score` | `scoring.overall` from the scoring formula |
| 7 | `score_components` | Full breakdown: `pain_explicitness`, `recurrence`, `business_cost`, `icp_fit`, `source_reliability`, `freshness`, `actionability`, `noise_risk` |
| 8 | `recurrence` | Raw evidence count in `source_evidence_list` |
| 9 | `source_diversity` | Count of distinct source types |
| 10 | `business_relevance` | 0.0–1.0 assessment |
| 11 | `noise_risk` | 0.0–1.0 assessment |
| 12 | `source_evidence_list` | List of evidence entries with `evidence_id`, `source_type`, `source_url`, `title`, `contribution_to_cluster` |
| 13 | `linked_candidate_signals` | `signal_id` list |
| 14 | `linked_opportunity_candidates` | `opportunity_id` list (if any) |
| 15 | `founder_review_recommendation` | Advisory recommendation: `review_for_promotion`, `needs_more_evidence`, `likely_noise`, `park_for_later` |

### 12.2 Cluster Rankings

Clusters are ranked by `overall_score` descending. Ties are broken by:
1. Higher `source_diversity` first
2. Higher `recurrence` first
3. Lower `noise_risk` first

---

## 13. Opportunity Candidate Reporting

### 13.1 Required Fields

Each opportunity candidate in the pilot run must include:

| # | Field | Type | Description |
|---|-------|------|-------------|
| 1 | `opportunity_id` | string | Stable identifier; format `oppc_<8char_hex>` |
| 2 | `source_pain_cluster_id` | string | The `cluster_id` this opportunity was framed from |
| 3 | `actor` / `icp` | string | Who experiences the pain; ICP alignment note |
| 4 | `problem_statement` | string | One-paragraph description of the problem |
| 5 | `evidence_summary` | string | Summary of the evidence supporting this opportunity |
| 6 | `source_evidence_links` | list[object] | Links to evidence: `{evidence_id, source_url, source_type}` |
| 7 | `score` | float | Inherited from the parent PainCluster `overall_score` |
| 8 | `uncertainty` | string | Assessment of evidence confidence: `low`, `moderate`, `high` |
| 9 | `suggested_validation_action` | string | Recommended next step: `interview`, `landing_page`, `manual_research`, `additional_evidence` |
| 10 | `founder_review_status` | string | Current review status: `pending_review`, `promoted`, `parked`, `killed`, `needs_more_evidence`, `revisit_later` |

### 13.2 Promotion Linkage

Every opportunity candidate must link back to its parent PainCluster and to the evidence items that support the pain. The traceability chain is:

```
source_url → RawEvidence → CandidateSignal → PainCluster → OpportunityCandidate
```

No opportunity candidate may exist without a complete, unbroken traceability chain.

---

## 14. Founder Review Loop

### 14.1 Review Statuses

Every pain cluster and opportunity candidate must receive one of these founder review statuses:

| Status | Meaning | Effect |
|--------|---------|--------|
| `PROMOTE` | Move forward: cluster accepted, opportunity candidate worth validating | `status → accepted` or `promoted_to_opportunity` |
| `PARK` | Interesting but not now; move to parking lot for revisit | `status → parked`; set revisit trigger |
| `KILL` | Not useful; document `KillReason` explaining why the idea died | `status → killed` |
| `NEEDS_MORE_EVIDENCE` | Plausible but insufficient; request additional collection | `status → needs_more_evidence`; trigger additional collection from under-represented sources |
| `REVISIT_LATER` | Possibly relevant in future; set revisit trigger | `status → parked` with revisit date |

### 14.2 Feedback Loop Integration

Founder decisions feed back into the system:

| Founder Action | Feedback Mechanism |
|----------------|-------------------|
| **KILL due to noise** | Adjust `noise_risk` prior for the source type; identify noise categories; tune noise filters |
| **KILL due to wrong ICP** | Adjust `icp_fit` calibration; refine ICP definition |
| **PROMOTE** | Validate scoring weights; confirm `pain_explicitness` and `business_cost` assessments |
| **PARK** | No score adjustment; cluster preserved for later |
| **NEEDS_MORE_EVIDENCE** | Trigger additional collection from under-represented sources; broaden query scope |

### 14.3 KillReason Requirement

Per OOS rules, `KillReason` must explain **why the idea died**, not just label it.

Good: "All three evidence items are self-promotion from the same author; no genuine user pain."
Bad: "Noise."

Good: "Pain is real but market is too small (single-actor problem with no recurrence across sources)."
Bad: "Not interesting."

### 14.4 Founder Review Package

The founder review package (`founder_review_package.json`) must present:
- Ranked list of pain clusters awaiting review
- Ranked list of opportunity candidates awaiting review
- For each: score breakdown, evidence links, representative quotes
- Clear action prompt: PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER
- Space for `KillReason` if killing
- Previous cycle's decisions for context

---

## 15. Weekly Pilot Report

### 15.1 Report Sections

Each weekly pilot run must produce a human-readable Markdown report with these sections:

| Section | Content |
|---------|---------|
| **Executive summary** | 2–3 paragraph overview: what ran, top findings, key decisions |
| **Top findings** | 3–5 most significant discoveries: pains, patterns, surprises |
| **Source quality summary** | Per-source metrics: records seen/emitted, accepted/weak/noise counts, signal rate, noise rate |
| **Top pain clusters** | Ranked list of clusters with scores, recurrence, source diversity, founder review recommendations |
| **Opportunity candidates** | List of opportunity candidates with problem statements, evidence strength, suggested validation actions |
| **Noise analysis** | Dominant noise categories, per-source noise breakdown, noise patterns that could be filtered |
| **Founder review queue** | Clusters and opportunity candidates awaiting founder decisions, with clear action prompts |
| **Suggested validation actions** | Interview targets, landing page test ideas, manual research directions |
| **Risks / caveats** | Known limitations: small sample size, source bias, fixture vs live gap, missing source types |
| **Next-cycle recommendations** | What to adjust for the next weekly cycle: query tuning, noise filter changes, source enablement, scoring weight suggestions |

### 15.2 Tone and Audience

The weekly pilot report is written for the **founder**. It must be:
- Clear and actionable — not technical documentation
- Honest about uncertainty and limitations
- Focused on decisions, not data volume
- Short enough to read in 10–15 minutes

---

## 16. Pilot Success Criteria

A **good result** after 1–2 weekly cycles:

| Metric | Expected Range |
|--------|---------------|
| Raw evidence items | 50–150 |
| Candidate signals | 10–30 |
| Pain clusters | 3–7 |
| Opportunity candidates | 3–5 |
| Ideas worth validation | At least 1–2 (via interview, landing page, or manual research) |
| Traceability | Every candidate has traceability to `source_url` / evidence |
| Cross-source clusters | At least 2 clusters with `source_diversity >= 2` |
| Candidate-tier clusters | At least 1–2 clusters scoring `overall >= 0.70` |

Success means the pipeline surfaces **real, specific business pains** that a founder would seriously consider validating. Not "produces many signals" — "produces signals worth acting on."

---

## 17. Pilot Failure Criteria

A **bad result** looks like:

- 90%+ of raw evidence is classified as noise
- Candidate signals are banal ("people want faster software", "AI is changing everything")
- Opportunity candidates are abstract and unactionable ("an AI-powered platform for developers")
- Founder review becomes manual trash sorting with no learning feedback
- Weekly review looks smart on paper but does not support actual decisions
- Candidate traceability is weak or missing (placeholder URLs, broken evidence chains)
- No cluster achieves `source_diversity >= 2` (no cross-source validation)
- Pain decomposition fields are vague or generic across all clusters

If the pilot fails, the Go/No-Go decision (v2.13) must recommend either:
- Fix the pipeline with specific, targeted improvements; OR
- Reconsider whether open-web pain discovery is the right top-of-funnel for OOS.

---

## 18. Go/No-Go Criteria

### 18.1 Go Criteria (Proceed to v2.14+ Source Expansion)

At least **all** of the following must be true:

| # | Criterion |
|---|-----------|
| G1 | At least 1–2 promising opportunity candidates surfaced |
| G2 | Founder review confirms usefulness (at least 1 PROMOTE decision on a non-trivial cluster) |
| G3 | Source noise is manageable (`noise_rate < 0.60` for each primary source) |
| G4 | Traceability is clean (zero placeholder URLs, zero missing source URLs) |
| G5 | Scoring and clustering are explainable (founder can understand why a cluster scored high/low) |
| G6 | At least 2 clusters have `source_diversity >= 2` (cross-source validation working) |

### 18.2 No-Go Criteria (Do Not Expand Sources)

Any of the following is a No-Go signal:

| # | Criterion |
|---|-----------|
| NG1 | No useful opportunity candidates surfaced (zero PROMOTE decisions) |
| NG2 | High founder review burden (founder spends >30 min/week on obvious noise) |
| NG3 | Clusters are vague or banal (no specific pain patterns identified) |
| NG4 | Scoring does not match founder judgement (systematic mismatch between scores and founder assessment) |
| NG5 | Sources produce mostly noise (`noise_rate >= 0.60` for all primary sources) |
| NG6 | Traceability chain is broken (placeholder URLs present, evidence links missing) |

### 18.3 Conditional Go (Proceed with Pipeline Fixes)

If the pilot produces 1–2 useful candidates but has quality issues (high noise, scoring misalignment), the recommendation is:
- Proceed to v2.12 (Pilot Quality Improvements) with targeted fixes
- Re-evaluate Go/No-Go after v2.12 improvements
- Do NOT expand sources until quality gates are met

---

## 19. Validation Policy

### 19.1 Testing Policy

| Rule | Policy |
|------|--------|
| Unit tests use fixtures only | **Mandatory.** No live API calls in unit tests. All test data comes from deterministic fixture files. |
| Live mode is opt-in only | **Mandatory.** Live source collection requires explicit founder approval and a separate controlled smoke test. |
| No live APIs in unit tests | **Mandatory.** Tests must pass without network access. |
| Source URL traceability required | **Mandatory.** Every evidence item must carry a real `http(s)://` URL. |
| Deterministic outputs required | **Mandatory.** Same fixture input → same output every run. |
| Controlled smoke must use bounded fixtures or explicit live approval | **Mandatory.** Smoke tests use fixtures by default; live smoke requires founder sign-off. |
| No deferred sources in pilot default path | **Mandatory.** HN + GitHub Issues only; Stack Exchange optional/stretch. |

### 19.2 Preflight Validation

Before each pilot run, the preflight phase (Section 9, Phase 1) must validate:
- Source registry configuration is valid
- All required fixture files exist (or live access is explicitly approved)
- Repo allowlist is non-empty for GitHub Issues source
- Scoring configuration is valid (weights sum correctly, thresholds are in range)
- No deferred sources are enabled

Preflight failure blocks the run.

### 19.3 Post-Run Validation

After each pilot run, the validation summary must confirm:
- All required output artifacts exist
- All fail rules from [`pain_cluster_contract.md`](pain_cluster_contract.md) Section 19 pass
- Source URL traceability report passes (zero missing, zero placeholder)
- Run ID is unique and follows the naming convention

---

## 20. Source-Specific Pilot Rules

### 20.1 Hacker News

| Rule | Detail |
|------|--------|
| **Prioritized content** | Ask HN, Show HN, and relevant comments are prioritized for signal extraction |
| **Noise flags** | Flamewars (heated arguments without constructive pain), launch hype (product announcements without pain), shallow comments (<50 chars, no substance), meta-discussion about HN itself |
| **Access method** | Algolia Search API (`hn.algolia.com`). Respect rate limits. |
| **URL pattern** | `https://news.ycombinator.com/item?id=<id>` for posts and comments |
| **Comment handling** | Comments are collected only when they independently express pain (distinct actor, same pain pattern). Comment volume alone is not signal. |
| **Fixture requirement** | Deterministic fixture file with representative Ask HN, Show HN, and comment examples |

### 20.2 GitHub Issues

| Rule | Detail |
|------|--------|
| **Repo allowlist** | **Mandatory.** Only issues from repos listed in `config/source_registry.json` are collected. |
| **PR filtering** | **Mandatory.** Pull requests must be filtered out. Only issues (not PRs) are collected. |
| **Issue URLs only** | `https://github.com/<owner>/<repo>/issues/<number>`. PR URLs (`/pull/`) must not appear in output. |
| **Comments optional / deferred** | Issue comments are collected only if they independently express pain. Default: comments deferred to v2.12. |
| **Staleness filter** | Issues with no activity in >365 days are flagged as `stale_abandoned` and routed to noise bucket. |
| **Low-context filter** | Issues with body <100 chars and no labels are flagged as `low_context_issue` and routed to weak/noise bucket. |
| **Fixture requirement** | Deterministic fixture file with representative issues from allowlisted repos |

### 20.3 Stack Exchange / Stack Overflow (Optional Stretch)

| Rule | Detail |
|------|--------|
| **Inclusion rule** | Include only if it does not slow the pilot cadence. Default: **excluded** from first 1–2 weekly cycles. |
| **Access method** | Official Stack Exchange API only. No scraping. |
| **URL pattern** | `https://stackoverflow.com/questions/<id>/<slug>` or `https://<site>.stackexchange.com/questions/<id>/<slug>` |
| **Signal extraction** | Questions that describe recurring technical friction. Answers are not signals unless they independently describe pain. |
| **Exclusion trigger** | If Stack Exchange collection adds >20% to total run time, exclude it and note in the source quality report. |

---

## 21. Traceability Requirements

Per [`source_url_traceability_contract.md`](source_url_traceability_contract.md), every artifact in the pilot run must maintain full source URL traceability:

| Rule | Applies To |
|------|-----------|
| Every raw evidence item has a real `source_url` using `http://` or `https://` scheme | `RawEvidence` records |
| Every candidate signal links to its source evidence | `CandidateSignal` objects |
| Every pain cluster links to its evidence list with URLs | `PainCluster.source_evidence_list` |
| Every opportunity candidate links to its cluster and evidence | `OpportunityCandidate` |
| No placeholder URLs or URNs (`urn:oos:*` or similar) anywhere | All artifacts |
| Source URL traceability report must pass (zero missing, zero placeholder) | Each pilot run |
| Every `source_url` must be the canonical, direct link to the source item | All evidence entries |

The traceability chain is:

```
source_url → RawEvidence.evidence_id → CandidateSignal.signal_id → PainCluster.cluster_id → OpportunityCandidate.opportunity_id
```

Every hop must be verifiable. A traceability index (`traceability_index.json`) maps each candidate back to its originating `source_url`(s).

---

## 22. Operational Constraints

The pilot run must operate under these constraints:

| Constraint | Detail |
|------------|--------|
| **Windows-native** | All scripts and commands run on Windows. PowerShell wrappers only. No bash/zsh dependencies. |
| **PowerShell wrappers** | All validation and execution uses `.ps1` scripts (e.g., `.\scripts\dev-git-check.ps1`, `.\scripts\dev-test.ps1`). |
| **No chained commands** | Each validation step uses a single wrapper script. No `&&` or `;` chaining for validation. |
| **No live APIs/LLMs in tests** | Unit tests use fixtures exclusively. No network calls. |
| **No default live source runs without approval** | Live collection requires explicit founder opt-in. Default is fixture mode. |
| **Deterministic fixtures** | All test fixtures produce identical output on every run. |
| **No broad scraping** | Each source has a defined, narrow access method (API, RSS, static allowlist). |
| **UTF-8 everywhere** | All files, artifacts, and reports use UTF-8 encoding. |

---

## 23. Pilot Retrospective

After 1–2 weekly cycles, the pilot retrospective must answer these questions:

| # | Question | Informs |
|---|----------|---------|
| 1 | Did OOS find useful business pains? | Go/No-Go decision |
| 2 | Which sources helped most? | Source reliability prior tuning |
| 3 | Which sources produced noise? | Noise filter design; source suspension consideration |
| 4 | Did scoring match founder judgement? | Scoring weight tuning in v2.12 |
| 5 | Did clusters make sense? | Clustering algorithm adequacy; pain decomposition quality |
| 6 | Did opportunity candidates suggest real validation actions? | Pipeline usefulness; founder value assessment |
| 7 | Should we improve the core pipeline before adding sources? | Prioritization: pipeline quality vs source expansion |
| 8 | Should v2.13 be Go or No-Go? | v2.13 decision input |

The retrospective is a structured document, not free-form notes. Each question must receive a clear answer with evidence from the pilot run.

---

## 24. Non-Goals

This contract explicitly excludes:

| Non-Goal | Rationale |
|----------|-----------|
| Implementation in this item | Contract definition only; no `.py` files modified |
| Source expansion beyond pilot set (HN + GitHub Issues + optional Stack Exchange) | Deferred to v2.14+, conditional on Go decision |
| Product Hunt / pimenov.ai implementation | Deferred to v2.14+ / context layer |
| Social/web scraping sources (Reddit, Discord, Slack, X/Twitter) | Deferred to v2.14+ |
| Automatic founder decisions | Founder review is mandatory and preserved |
| LLM-based validation in default tests | All scoring is deterministic; no LLM required |
| UI/dashboard work | Not in scope |
| Database or persistent server architecture | File-system artifacts only |
| Generating artifacts, fixtures, or test data | Implementation concern |
| Running the pilot | This contract defines the design; execution requires separate authorization |
| Modifying existing source code, tests, scripts, or artifacts | Docs-only item |

---

## 25. Decision

**v2.11 item 9 defines the Operational Discovery Pilot Run and Source Quality Report Contract only.**

- No pilot run behavior is implemented.
- No runtime behavior is changed.
- No artifacts are generated.
- No source code, tests, scripts, or configuration files are modified.
- The contract defines the pilot run lifecycle (14 phases), source quality report structure (8 sections), source quality metrics (18 metrics), PainCluster and opportunity candidate reporting fields, founder review loop, weekly pilot report structure, success/failure criteria, Go/No-Go criteria, validation policy, source-specific rules, traceability requirements, operational constraints, and retrospective questions.
- Implementation of the pilot run, source quality report generation, and weekly cadence requires later roadmap items and explicit founder approval.

---

## 26. Self-Audit

| Question | Answer |
|----------|--------|
| Did this avoid implementation? | **Yes.** Contract/advisory only. No `.py` files modified. |
| Did this avoid source/test changes? | **Yes.** No source, test, script, or example files changed. |
| Did this define title and status? | **Yes.** Section 1. |
| Did this define context? | **Yes.** Section 2 explains the pilot purpose and source scope. |
| Did this define pilot objective? | **Yes.** Section 3 defines 6 questions and operational steps. |
| Did this define pilot scope? | **Yes.** Section 4 lists 9 activities. |
| Did this define explicit non-scope? | **Yes.** Section 5 lists 12 excluded sources + 7 excluded activities. |
| Did this define pilot run inputs? | **Yes.** Section 6 defines 9 input types with fixture/live modes. |
| Did this define pilot run outputs? | **Yes.** Section 7 defines 10 required outputs. |
| Did this define artifact locations? | **Yes.** Section 8 defines proposed paths with run ID format. |
| Did this define pilot run lifecycle? | **Yes.** Section 9 defines 14 phases in order with inputs/outputs. |
| Did this define source quality report structure? | **Yes.** Section 10 defines 8 required sections with JSON schema sketch. |
| Did this define source quality metrics? | **Yes.** Section 11 defines 18 metrics. |
| Did this define PainCluster reporting? | **Yes.** Section 12 defines 15 report fields and ranking rules. |
| Did this define opportunity candidate reporting? | **Yes.** Section 13 defines 10 required fields and traceability linkage. |
| Did this define founder review loop? | **Yes.** Section 14 defines 5 statuses, feedback loop, KillReason, and review package. |
| Did this define weekly pilot report? | **Yes.** Section 15 defines 10 report sections with audience guidance. |
| Did this define pilot success criteria? | **Yes.** Section 16 defines 7 success metrics. |
| Did this define pilot failure criteria? | **Yes.** Section 17 defines 7 failure indicators. |
| Did this define Go/No-Go criteria? | **Yes.** Section 18 defines 6 Go criteria, 6 No-Go criteria, and conditional Go path. |
| Did this define validation policy? | **Yes.** Section 19 defines testing policy, preflight validation, and post-run validation. |
| Did this define source-specific pilot rules? | **Yes.** Section 20 defines rules for HN, GitHub Issues, and Stack Exchange. |
| Did this define traceability requirements? | **Yes.** Section 21 defines 6 rules plus traceability chain diagram. |
| Did this define operational constraints? | **Yes.** Section 22 defines 7 constraints. |
| Did this define pilot retrospective? | **Yes.** Section 23 defines 8 retrospective questions. |
| Did this state non-goals? | **Yes.** Section 24 lists 12 explicit non-goals. |
| Did this state the decision? | **Yes.** Section 25. |
| Did this reference all predecessor documents? | **Yes.** Dependencies header lists all 8 predecessor contracts/decisions. |
| Did this respect the non-goals? | **Yes.** No implementation, no LLM, no live APIs, no source modification. |

---

*Operational Discovery Pilot Run and Source Quality Report Contract. v2.11 item 9. Contract finalized / implementation pending.*
