# PainCluster Contract and Scoring Formula

**Version:** pain_cluster_contract.v1
**Roadmap:** v2.11
**Item:** 8
**Status:** Contract finalized / implementation pending
**Depends on:**
- [`operational_discovery_pilot_reorientation_v2_11.md`](../decisions/operational_discovery_pilot_reorientation_v2_11.md) (v2.11 item 7)
- [`discovery_source_adapter_contract.md`](discovery_source_adapter_contract.md) (v2.11 item 1)
- [`raw_evidence_artifact_schema.md`](raw_evidence_artifact_schema.md) (v2.11 item 2)
- [`source_url_traceability_contract.md`](source_url_traceability_contract.md) (v2.7 item 1.1)
**Precedes:**
- Roadmap v2.11 item 9 — Pilot Run Design and Source Quality Report Contract
- Roadmap v2.12 — Pilot Quality Improvements (scoring weight tuning)

---

## 1. Context

### 1.1 Why PainCluster Exists

v2.11 is reoriented into an **Operational Discovery Pilot**. The pilot must test whether OOS finds useful business pains from HN + GitHub Issues (with optional Stack Exchange), not merely classify source noise.

The existing pipeline already has:
- [`RawEvidence`](../../src/oos/models.py:77) — normalized source items from adapters
- [`CandidateSignal`](../../src/oos/models.py:228) — extracted pain signals from individual evidence items
- [`SemanticCluster`](../../src/oos/semantic_clustering.py:34) — LLM-driven grouping of [`Signal`](../../src/oos/models.py:483) objects
- [`ClusterSynthesis`](../../src/oos/models.py:438) — LLM-driven synthesis of 5-10 signals into opportunity sketches
- [`WeakPatternCandidate`](../../src/oos/models.py:381) — rule-based aggregator for weak signals (5+ signals, source diversity >= 2)

What is missing is a **first-class pilot artifact** that:

1. Groups raw evidence and candidate signals by **pain pattern** across sources **before** they feed into opportunity framing.
2. Provides a **deterministic, explainable score** for each pain cluster.
3. Enforces **cross-source consolidation**: the same pain appearing in HN, GitHub Issues, and optional Stack Exchange must become **one cluster with multiple evidence points**, not multiple duplicate ideas.
4. Surfaces clusters for **founder review** with enough context to decide PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER.

**PainCluster** is that artifact.

### 1.2 PainCluster in the Pipeline

```
RawEvidence                    CandidateSignal              PainCluster                   OpportunityCandidate
───────────                    ───────────────              ───────────                   ────────────────────
evidence_id          →         signal_id                    cluster_id                    opportunity_id
source_url           →         source_url                   source_evidence_list[]        source_urls[]
title + body         →         pain_summary                 actor / workflow / object     opportunity_description
evidence_kind        →         signal_type                  pain_pattern                  (framed from cluster)
quality_flags        →         confidence                   recurrence                    icp_fit
raw_metadata         →         traceability                 business_relevance            evidence_summary
                                                             noise_risk
                                                             scoring (deterministic)
```

PainCluster sits between candidate signals and opportunity candidates. It consolidates evidence across sources, applies the pain-first scoring formula, and presents clusters for founder review before any opportunity framing occurs.

### 1.3 Core Design Principle

Same pain observed across HN, GitHub Issues, and optional Stack Exchange **must become one PainCluster with multiple evidence points**, not multiple separate ideas. Cross-source consolidation is mandatory. Source diversity is a strength signal, not a duplication problem.

---

## 2. Relationship to Existing System

### 2.1 What Already Exists

| Existing Artifact | Module | Role | Relationship to PainCluster |
|-------------------|--------|------|----------------------------|
| [`RawEvidence`](../../src/oos/models.py:77) | `models.py` | Normalized source items from adapters | Feeds into PainCluster as evidence entries |
| [`CandidateSignal`](../../src/oos/models.py:228) | `models.py` | Extracted pain signals from individual evidence | Linked from PainCluster via `linked_candidate_signals` |
| [`Signal`](../../src/oos/models.py:483) | `models.py` | Older signal model with validity dimensions (specificity, recurrence, workaround, cost_signal, icp_match) | Conceptual ancestor; PainCluster uses similar dimensions but scored 0.0–1.0 instead of integer 0-5 |
| [`SignalScoreBreakdown`](../../src/oos/signal_scoring.py:83) | `signal_scoring.py` | Per-signal scoring with embeddings-disabled weights (topic_relevance, pain_strength, workaround, buying_intent, urgency, source_quality, customer_voice) | PainCluster scoring is **cluster-level**, not signal-level; uses different components (pain_explicitness, recurrence, business_cost, icp_fit, source_reliability, freshness, actionability, noise_risk) |
| [`SemanticCluster`](../../src/oos/semantic_clustering.py:34) | `semantic_clustering.py` | LLM-driven grouping of Signal objects with title, summary, confidence, uncertainty | Different layer: SemanticCluster groups `Signal` objects via LLM; PainCluster groups `CandidateSignal` + `RawEvidence` deterministically by pain pattern |
| [`ClusterSynthesis`](../../src/oos/models.py:438) | `models.py` | LLM-driven synthesis of 5-10 signals into opportunity sketches with emerging_pain_pattern, icp_synthesis, opportunity_sketch, why_now_signal | Downstream of PainCluster: ClusterSynthesis operates on signal groups that have already been clustered by pain pattern |
| [`WeakPatternCandidate`](../../src/oos/models.py:381) | `models.py` | Rule-based aggregator for weak signals (5+ signals, source_diversity >= 2, max_confidence < 0.60) | Conceptual overlap: both are rule-based cluster-level artifacts. PainCluster replaces/absorbs this role for the pilot with a richer schema. |
| [`SourceQualityWeights`](../../src/oos/signal_scoring.py:41) | `signal_scoring.py` | Per-source weight constants (github_issues: 0.78, hacker_news_algolia: 0.72, stack_exchange: 0.62, rss_feed: 0.45) | PainCluster uses `source_reliability` component with similar priors (Section 15) |

### 2.2 What PainCluster Should Reuse Conceptually

- **Deterministic scoring** philosophy from [`signal_scoring.py`](../../src/oos/signal_scoring.py) — all components must be explainable from evidence, no LLM required for scoring.
- **Validation rigor** from existing models — every field validated, every score clamped to 0.0–1.0.
- **Traceability** from [`source_url_traceability_contract.md`](source_url_traceability_contract.md) — every evidence entry must carry a real `source_url`.
- **Cluster identity** concept from [`WeakPatternCandidate`](../../src/oos/models.py:381) — `cluster_key` as stable identity based on content, not timestamps.
- **Artifact persistence** pattern from the existing artifact store — structured JSON files under `artifacts/discovery/`.

### 2.3 What Must Not Be Broken

- Existing [`CandidateSignal`](../../src/oos/models.py:228) extraction pipeline — PainCluster reads CandidateSignals, does not modify them.
- Existing [`SignalScoreBreakdown`](../../src/oos/signal_scoring.py:83) — PainCluster scoring is additive (cluster-level), not replacement.
- Existing [`ClusterSynthesis`](../../src/oos/models.py:438) — PainCluster feeds into it; ClusterSynthesis continues to operate on signal groups.
- Existing [`SemanticCluster`](../../src/oos/semantic_clustering.py:34) — different artifact for different layer; no conflict.
- Weekly run artifacts — PainCluster artifacts are new additions, not modifications to existing artifacts.

### 2.4 Where Implementation May Later Integrate

- A new `src/oos/pain_cluster.py` module (not authorized by this contract).
- Integration into [`discovery_weekly.py`](../../src/oos/discovery_weekly.py) after candidate signal extraction.
- New artifact directory `artifacts/discovery/pain_clusters/`.
- New validation in the weekly cycle validation pass.
- Founder review UI integration (not in v2.11 scope).

---

## 3. PainCluster Definition

### 3.1 Minimum Fields

| # | Field | Type | Required | Description |
|---|-------|------|----------|-------------|
| 1 | `cluster_id` | `string` | **Yes** | Stable, deterministic identifier (see Section 6) |
| 2 | `actor` | `string` | **Yes** | Who experiences the pain (role, persona) |
| 3 | `workflow` | `string` | **Yes** | The task or workflow being disrupted |
| 4 | `object` | `string` | **Yes** | The tool, system, or process causing the pain |
| 5 | `pain_verb` | `string` | **Yes** | The specific pain action (e.g., "cannot integrate", "loses data") |
| 6 | `pain_pattern` | `string` | **Yes** | Normalized pain statement combining actor + workflow + object + pain_verb |
| 7 | `source_evidence_list` | `list[object]` | **Yes** | All evidence entries supporting this cluster (see Section 8) |
| 8 | `source_diversity` | `int` | **Yes** | Count of distinct source types (e.g., HN + GitHub Issues = 2) |
| 9 | `recurrence` | `int` | **Yes** | Number of distinct evidence items expressing this pain |
| 10 | `business_relevance` | `float` | **Yes** | 0.0–1.0 estimate of whether this pain could support a business |
| 11 | `noise_risk` | `float` | **Yes** | 0.0–1.0 estimate that this cluster is noise, not real pain |
| 12 | `representative_quotes_or_excerpts` | `list[string]` | **Yes** | Short excerpts (≤200 chars each) capturing the pain in source words |
| 13 | `linked_candidate_signals` | `list[string]` | **Yes** | `signal_id` values of CandidateSignals feeding this cluster |
| 14 | `linked_opportunity_candidates` | `list[string]` | **No** | `opportunity_id` values if opportunity candidates were formed |
| 15 | `created_at` | `string` | **Yes** | ISO 8601 UTC timestamp of cluster creation |
| 16 | `updated_at` | `string` | **Yes** | ISO 8601 UTC timestamp of last update |
| 17 | `status` | `string` | **Yes** | Cluster lifecycle status (see Section 16) |
| 18 | `scoring` | `object` | **Yes** | Full scoring breakdown (see Section 13) |
| 19 | `notes` | `string` | **No** | Free-form notes, founder annotations, implementation remarks |

### 3.2 Field Definitions in Detail

#### 3.2.1 `cluster_id`

- **Type:** `string`
- **Required:** Yes
- **Generation rule (deterministic, for later implementation):** `SHA-256(normalized_actor + "|" + normalized_workflow + "|" + normalized_object + "|" + normalized_pain_pattern)[:16]` prefixed with `pc_` (e.g., `pc_a1b2c3d4e5f6a7b8`).
- **Stability:** Same normalized actor + workflow + object + pain_pattern → same `cluster_id` across runs.
- **No timestamps in identity.**
- **Evidence count changes do not change identity.**

#### 3.2.2 `actor`

- **Type:** `string`
- **Required:** Yes
- **Description:** Who has the pain. Normalized to a role/persona label (e.g., "developer", "devops engineer", "data scientist", "founder", "finance manager", "compliance officer"). Not a username, not a company name.
- **Validation:** Non-empty, not "unknown" (if truly unknown after best efforts, use "unidentified_actor" and set `noise_risk` accordingly).

#### 3.2.3 `workflow`

- **Type:** `string`
- **Required:** Yes
- **Description:** The process or workflow being disrupted. Normalized to a short action phrase (e.g., "AI agent debugging", "CI/CD pipeline management", "multi-cloud deployment", "invoice reconciliation", "compliance audit preparation").
- **Validation:** Non-empty, not "unknown".

#### 3.2.4 `object`

- **Type:** `string`
- **Required:** Yes
- **Description:** The tool, data, entity, or process involved in the pain. Normalized to a noun phrase (e.g., "multi-step agent workflows", "Kubernetes clusters", "spreadsheet-based reports", "regulatory filings").
- **Validation:** Non-empty, not "unknown".

#### 3.2.5 `pain_verb`

- **Type:** `string`
- **Required:** Yes
- **Description:** The specific pain action — what hurts. Normalized to a short verb phrase (e.g., "hard to debug", "unreliable", "manual workaround required", "costs too much", "cannot integrate", "loses data", "too slow", "breaks silently").
- **Validation:** Non-empty, not "unknown". Must be a specific action, not a vague adjective.

#### 3.2.6 `pain_pattern`

- **Type:** `string`
- **Required:** Yes
- **Description:** Normalized pain statement combining all decomposition fields. Format: `"{actor} cannot {workflow} because {object} {pain_verb}"` or a semantically equivalent single sentence.
- **Example:** `"developers cannot reliably debug AI agent workflows because multi-step agent execution is hard to trace and reproduce"`
- **Validation:** Non-empty. Must contain the actor, workflow, object, and pain_verb in a readable single sentence.

#### 3.2.7 `source_evidence_list`

- **Type:** `list[object]` — each entry is an evidence object (see Section 8).
- **Required:** Yes
- **Validation:** Must contain at least 1 entry. Each entry must have a real `source_url`.

#### 3.2.8 `source_diversity`

- **Type:** `int`
- **Required:** Yes
- **Description:** Count of distinct `source_type` values across all evidence entries. Possible values: 1 (single-source), 2 (two distinct source types, e.g., HN + GitHub Issues), 3 (HN + GitHub Issues + Stack Exchange).
- **Deterministic generation:** Count unique `source_type` values in `source_evidence_list`.
- **Validation:** >= 1. Must match the actual distinct source types in the evidence list.

#### 3.2.9 `recurrence`

- **Type:** `int`
- **Required:** Yes
- **Description:** Number of distinct evidence items in `source_evidence_list`. This is the raw count of evidence points, not a normalized score.
- **Deterministic generation:** `len(source_evidence_list)` after deduplication within the cluster.
- **Validation:** >= 1. Must match the actual length of `source_evidence_list`.

#### 3.2.10 `business_relevance`

- **Type:** `float`
- **Required:** Yes
- **Range:** 0.0–1.0
- **Description:** Estimate of whether this pain could support a business (see Section 11 for detailed rules).
- **Validation:** 0.0 <= value <= 1.0.

#### 3.2.11 `noise_risk`

- **Type:** `float`
- **Required:** Yes
- **Range:** 0.0–1.0
- **Description:** Estimate that this cluster is noise, not real pain (see Section 12 for noise categories).
- **Validation:** 0.0 <= value <= 1.0.

#### 3.2.12 `representative_quotes_or_excerpts`

- **Type:** `list[string]`
- **Required:** Yes
- **Description:** Short excerpts (≤200 characters each) from the source evidence that capture the pain in the user's own words. At least 1, at most 5.
- **Validation:** Non-empty list. Each string ≤ 200 characters.

#### 3.2.13 `linked_candidate_signals`

- **Type:** `list[string]`
- **Required:** Yes
- **Description:** `signal_id` values of [`CandidateSignal`](../../src/oos/models.py:228) objects feeding this cluster. May be empty if no candidate signals have been extracted yet (evidence-only cluster).
- **Validation:** Each ID must be a non-empty string. Duplicates are not allowed.

#### 3.2.14 `linked_opportunity_candidates`

- **Type:** `list[string]`
- **Required:** No
- **Description:** `opportunity_id` values if opportunity candidates have been formed from this cluster. Empty if no opportunity framing has occurred.
- **Validation:** Each ID must be a non-empty string when present.

#### 3.2.15 `created_at`

- **Type:** `string`
- **Required:** Yes
- **Description:** ISO 8601 UTC timestamp of when this cluster was first created. Set once, never changed.
- **Format:** `YYYY-MM-DDTHH:MM:SSZ`
- **Validation:** Valid ISO 8601 UTC timestamp.

#### 3.2.16 `updated_at`

- **Type:** `string`
- **Required:** Yes
- **Description:** ISO 8601 UTC timestamp of last update (new evidence added, status changed, scoring recalculated).
- **Format:** `YYYY-MM-DDTHH:MM:SSZ`
- **Validation:** Valid ISO 8601 UTC timestamp. Must be >= `created_at`.

#### 3.2.17 `status`

- **Type:** `string`
- **Required:** Yes
- **Description:** Cluster lifecycle status (see Section 16 for full status lifecycle).
- **Allowed values:** `new`, `accepted`, `weak`, `noise`, `needs_more_evidence`, `promoted_to_opportunity`, `parked`, `killed`.
- **Default:** `new` on creation.

#### 3.2.18 `scoring`

- **Type:** `object`
- **Required:** Yes
- **Description:** Full scoring breakdown (see Sections 13–14).
- **Structure:**
  ```json
  {
    "overall": 0.0,
    "pain_explicitness": 0.0,
    "recurrence": 0.0,
    "business_cost": 0.0,
    "icp_fit": 0.0,
    "source_reliability": 0.0,
    "freshness": 0.0,
    "actionability": 0.0,
    "noise_risk": 0.0,
    "scoring_model_version": "pain_cluster_scoring_v1_pilot",
    "computed_at": "2026-05-12T00:00:00Z"
  }
  ```
- **Validation:** All component scores must be 0.0–1.0. `overall` must equal the weighted formula result (Section 13) clamped to 0.0–1.0.

#### 3.2.19 `notes`

- **Type:** `string`
- **Required:** No
- **Description:** Free-form notes. Founder annotations, implementation remarks, review comments. May be empty.
- **Validation:** None beyond type check.

---

## 4. Cluster Identity Rules

### 4.1 Deterministic `cluster_id` Generation

`cluster_id` must be **stable and deterministic** based on normalized pain pattern fields:

```
normalized_actor = lowercase(trim(actor))
normalized_workflow = lowercase(trim(workflow))
normalized_object = lowercase(trim(object))
normalized_pain_pattern = lowercase(trim(pain_pattern))

cluster_key = normalized_actor + "|" + normalized_workflow + "|" + normalized_object + "|" + normalized_pain_pattern
cluster_id = "pc_" + SHA-256(cluster_key)[:16]
```

**Rules:**
- Same normalized actor + workflow + object + pain_pattern → same `cluster_id` across runs, across days.
- Timestamps are NOT part of identity.
- Evidence count changes do NOT change identity — new evidence attaches to existing cluster if the pain pattern matches.
- Case-insensitive normalization prevents near-duplicate clusters from minor case differences.

### 4.2 Cross-Source Evidence Attachment

When new evidence is discovered from a different source but matches the pain pattern of an existing cluster:

- The evidence is **attached to the existing cluster** (added to `source_evidence_list`).
- `recurrence` is incremented.
- `source_diversity` is recalculated.
- `scoring` is recalculated with the new evidence.
- `updated_at` is set to now.
- A new cluster is NOT created.

### 4.3 Cluster Identity vs Cluster Content

| Changes... | Identity | Action |
|------------|----------|--------|
| Actor, workflow, object, or pain_pattern changes | Identity changes | New cluster; old cluster may be marked as merged |
| Evidence added from same source | Identity unchanged | Update existing cluster |
| Evidence added from new source | Identity unchanged | Update existing cluster; recalculate source_diversity |
| Status changes | Identity unchanged | Update `status` and `updated_at` |
| Scoring recalculated | Identity unchanged | Update `scoring` and `updated_at` |

---

## 5. Pain Pattern Decomposition

### 5.1 Decomposition Fields

Every PainCluster must decompose the pain into four dimensions:

| Dimension | Question Answered | Example |
|-----------|------------------|---------|
| `actor` | Who has the pain? | "developer" |
| `workflow` | What process/workflow is affected? | "AI agent debugging" |
| `object` | What tool/data/entity/process is involved? | "multi-step agent workflows" |
| `pain_verb` | What hurts? | "hard to debug / unreliable" |

### 5.2 Decomposition Rules

- **Actor must be a role/persona**, not an individual, company, or username.
- **Workflow must be a specific process**, not a vague domain (e.g., "debugging" is too vague; "AI agent debugging" is specific).
- **Object must be concrete** — the thing that causes or is involved in the pain (tool, system, data, entity).
- **Pain_verb must be specific and actionable** — "hard to debug", "unreliable", "manual workaround required", "too expensive", "cannot integrate", "loses data". Reject vague verbs like "bad", "problem", "issue".

### 5.3 Normalization

All decomposition fields should be:
- Lowercased for normalization (identity purposes).
- Trimmed of leading/trailing whitespace.
- Free of source-specific jargon unless the jargon is the pain itself.
- Written in plain English, not marketing language.

### 5.4 Complete Example

```
actor: developer
workflow: AI agent debugging
object: multi-step agent workflows
pain_verb: hard to debug / unreliable

pain_pattern: "developers cannot reliably debug AI agent workflows because multi-step agent execution is hard to trace and reproduce"
```

This pattern would match evidence like:
- HN post: "Debugging AI agents is a nightmare — you can't step through their reasoning"
- GitHub issue: "Agent execution traces are not reproducible across runs"
- SO question: "How to debug multi-step LLM agent workflows?"

All three would become **one PainCluster**, not three separate ideas.

---

## 6. Source Evidence List

### 6.1 Evidence Entry Schema

Each entry in `source_evidence_list` is an object with these fields:

| # | Field | Type | Required | Description |
|---|-------|------|----------|-------------|
| 1 | `evidence_id` | `string` | **Yes** | Stable ID from [`RawEvidence.evidence_id`](../../src/oos/models.py:78) |
| 2 | `source_id` | `string` | **Yes** | Source identifier (e.g., `hacker_news_algolia`, `github_issues`) |
| 3 | `source_type` | `string` | **Yes** | Source category: `discussion`, `issue_tracker`, `qa` |
| 4 | `source_url` | `string` | **Yes** | Real, stable `http(s)://` URL to the source item |
| 5 | `evidence_kind` | `string` | **Yes** | Classification hint from [`RawEvidence`](../../src/oos/models.py:77) or downstream classifier |
| 6 | `title` | `string` | **Yes** | Source item title |
| 7 | `excerpt` | `string` | **Yes** | Relevant excerpt (≤500 chars) showing the pain |
| 8 | `created_at` | `string` | **Yes** | Original item creation timestamp (ISO 8601) |
| 9 | `fetched_at` | `string` | **Yes** | When this evidence was fetched (ISO 8601) |
| 10 | `signal_id` | `string` or `null` | **No** | `signal_id` if already converted to CandidateSignal |
| 11 | `contribution_to_cluster` | `string` | **Yes** | How this evidence contributes: `primary_pain`, `supporting_pain`, `workaround_description`, `cost_evidence`, `context_only` |
| 12 | `quality_flags` | `list[string]` | **No** | Quality flags from [`RawEvidence`](../../src/oos/models.py:77) or adapter |

### 6.2 Source URL Traceability

Every evidence entry **must** carry a real, stable `source_url` using `http://` or `https://` scheme. Per [`source_url_traceability_contract.md`](source_url_traceability_contract.md):

- No `urn:oos:*` placeholders. Ever.
- The URL must be the canonical, direct link to the source item.
- Missing `source_url` is a validation **failure** (error).

### 6.3 Contribution Types

| `contribution_to_cluster` | Meaning |
|---------------------------|---------|
| `primary_pain` | This evidence directly expresses the core pain |
| `supporting_pain` | This evidence supports the pain but is less explicit |
| `workaround_description` | This evidence describes a workaround, implying the pain |
| `cost_evidence` | This evidence quantifies the cost of the pain |
| `context_only` | This evidence provides context but does not directly express pain |

At least one evidence entry must have `contribution_to_cluster: primary_pain`.

---

## 7. Source Diversity

### 7.1 Definition

`source_diversity` is the count of distinct `source_type` values across all evidence entries in the cluster.

### 7.2 Diversity Strength

| Source Diversity | Assessment | Implication |
|-----------------|------------|-------------|
| 1 (single-source) | Weak | Pain may be source-specific or echo-chamber |
| 2 (two sources) | Moderate | HN + GitHub Issues cross-validation; stronger signal |
| 3 (three sources) | Strong | HN + GitHub Issues + Stack Exchange; robust evidence |
| 4+ | Very strong | Requires additional sources beyond pilot scope; deferred |

### 7.3 Cross-Source vs Same-Source Recurrence

- **Same-source recurrence** (e.g., multiple HN posts about the same pain) has value but is weaker than cross-source.
- **Cross-source recurrence** (e.g., HN discussion + GitHub issue + SO question about the same pain) is stronger evidence that the pain is real and not source-specific noise.
- Source diversity boosts `recurrence` in the scoring formula (Section 13) via quality multiplier.

### 7.4 Over-Counting Prevention

- Do NOT count the same evidence item twice because it was fetched via different query kinds.
- Do NOT count cross-posted content as distinct evidence (e.g., same post on HN and Reddit — but Reddit is excluded from pilot).
- Do NOT count comments on the same thread as distinct evidence items unless each comment represents a distinct actor expressing the same pain independently.
- If the same GitHub issue is referenced in an HN post, the HN post and GitHub issue are distinct evidence items (different sources, different actors).

---

## 8. Recurrence Rules

### 8.1 What Counts as Recurrence

Recurrence is the count of **distinct evidence items** expressing the same or semantically equivalent pain pattern. Recurrence is NOT:

- Comment count or upvote count on a single post.
- Number of times a keyword appears.
- Number of source items mentioning the same tool/product.
- Popularity or virality metrics.

### 8.2 Valid Recurrence Signals

| Signal | Counts as Recurrence? | Notes |
|--------|----------------------|-------|
| Multiple HN posts from different users about the same pain | **Yes** | Each post = 1 evidence item |
| Multiple GitHub issues from different repos about the same pain | **Yes** | Each issue = 1 evidence item |
| HN post + GitHub issue about the same pain | **Yes** | Cross-source = stronger |
| Multiple comments on the same HN post | **Yes, if** each comment is from a different user independently expressing the pain | Moderate value |
| Same user posting the same complaint in multiple threads | **Partially** | Count once per distinct thread; flag as potential single-actor bias |
| Upvotes/likes on a post | **No** | Not recurrence |
| Shares/retweets | **No** | Not recurrence |
| Search result count for a keyword | **No** | Not recurrence |

### 8.3 Recurrence Normalization for Scoring

For the scoring formula, raw recurrence count is normalized to 0.0–1.0:

```
recurrence_score = min(1.0, raw_recurrence_count / 5.0)
```

Where `raw_recurrence_count` is the number of distinct evidence items. A cluster with 5+ evidence items scores 1.0 on recurrence. Pilot default: this is a linear normalization; if pilot data shows bimodal distribution, normalization may be tuned in v2.12.

### 8.4 Cross-Source Recurrence Bonus

Cross-source recurrence receives a quality multiplier in the scoring formula:

- `source_diversity == 1`: no bonus (standard recurrence normalization).
- `source_diversity >= 2`: `recurrence_score` is multiplied by 1.15 (capped at 1.0).
- This is applied in the `recurrence` scoring component.

---

## 9. Business Relevance Rules

### 9.1 Definition

`business_relevance` estimates whether the pain could support a viable business. It answers: "If we solve this pain, would someone pay for it?"

### 9.2 Indicators of Business Relevance

| Positive Indicator | Weight Signal | Example |
|--------------------|---------------|---------|
| Direct cost mentioned | Strong | "We spend $500/month on workarounds" |
| Time loss quantified | Strong | "This takes 10 hours/week per engineer" |
| Revenue loss implied | Strong | "We lose customers because of this" |
| Compliance/risk issue | Strong | "We failed an audit because of this" |
| Manual labor required | Moderate | "I have to manually reconcile these every week" |
| Tool spend mentioned | Moderate | "We pay for three tools to do what one should do" |
| Support burden described | Moderate | "Our support team spends 40% of time on this" |
| Customer churn linked | Strong | "Users leave because of this friction" |
| Workflow breakage | Moderate | "Our CI/CD pipeline breaks and blocks deploys" |
| Scaling pain | Moderate | "This works for 10 users but not 100" |

### 9.3 Non-Business Indicators

| Non-Business Indicator | Assessment |
|------------------------|------------|
| Hobby project pain | Low relevance unless linked to paid workflow |
| Personal preference complaint | Low relevance unless widespread |
| Aesthetic complaint | Low relevance |
| Political/ideological complaint | Not business pain |
| Entertainment/fun complaint | Not business pain |
| One-person annoyance | Low relevance; needs recurrence |

### 9.4 Founder/Developer Pain Qualification

Founder or developer pain **may be business-relevant** if:
- The pain affects a paid/commercial workflow (not a hobby project).
- The pain is in a domain where tools are purchased (devtools, infrastructure, SaaS).
- The pain has clear cost implications (time = money for paid developers).
- The pain is shared by multiple actors across organizations.

Founder/developer pain in hobby or free-tier contexts should be scored lower on business relevance.

### 9.5 Scoring Guidance for `business_relevance`

| Score | Criteria |
|-------|----------|
| 0.0 | No business relevance; hobby, entertainment, personal preference |
| 0.3 | Weak relevance; single-actor pain, no cost mentioned, unclear market |
| 0.5 | Moderate relevance; pain affects business workflows, some cost implied |
| 0.7 | Strong relevance; clear cost/time/revenue impact, multiple actors |
| 1.0 | Very strong relevance; quantified cost, compliance/risk, proven willingness to pay |

---

## 10. Noise Risk Rules

### 10.1 Definition

`noise_risk` estimates the probability that this cluster is noise — not a real, actionable business pain. High noise risk should suppress the overall score.

### 10.2 Noise Categories

| Noise Category | Description | Example |
|----------------|-------------|---------|
| `flamewar` | Heated argument, not constructive pain discussion | "Rust vs Go debate with insults" |
| `self_promotion` | Someone promoting their own product/service | "Check out my new AI tool!" |
| `vague_complaint` | Complaint without specific actor, workflow, or object | "Everything sucks, nothing works" |
| `low_context_issue` | GitHub issue with minimal description | "It's broken. Fix it." |
| `one_off_bug` | A bug affecting one user in one specific context | "This crashes when I use Python 3.7 on Windows XP" |
| `non_business_hobby` | Pain in a hobby/free context with no business implications | "My Home Assistant dashboard is ugly" |
| `launch_hype` | Product launch announcement, not pain | "We just launched our MVP!" |
| `stale_abandoned` | Old issue with no recent activity, likely resolved or abandoned | GitHub issue from 2019 with no comments since 2020 |
| `bot_generated` | Content generated by bots, scrapers, or automated systems | Automated dependency update PRs, bot-generated issues |
| `duplicate_evidence` | Near-duplicate of another evidence item (should be deduplicated, not clustered) | Cross-post of the same content |
| `unclear_actor_workflow` | Missing or unidentifiable actor/workflow | "Something is wrong with the thing" |

### 10.3 Scoring Guidance for `noise_risk`

| Score | Criteria |
|-------|----------|
| 0.0 | Clean signal; no noise indicators present |
| 0.2 | Minor noise concern; one weak noise indicator |
| 0.4 | Moderate noise concern; multiple weak indicators or one strong indicator |
| 0.6 | Significant noise concern; evidence is substantially noisy |
| 0.8 | High noise probability; cluster is likely noise but has one redeeming quality |
| 1.0 | Certain noise; cluster should be marked `noise` |

### 10.4 Noise and Scoring

`noise_risk` is a **penalty** in the scoring formula (subtracted at 0.20 weight). High noise risk can drive a cluster's overall score below promotion thresholds.

---

## 11. Explicit Scoring Formula

### 11.1 Formula

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

### 11.2 Constraints

- All component scores MUST be normalized to 0.0–1.0 before applying weights.
- `overall` MUST be clamped to 0.0–1.0 after computation.
- Weights sum to: 0.25 + 0.20 + 0.15 + 0.15 + 0.10 + 0.10 + 0.05 - 0.20 = 0.80 (positive weights) with a -0.20 noise penalty. Effective range: [-0.20, 0.80] before clamping.
- Clamping ensures overall is never negative and never exceeds 1.0.
- All components must be **explainable from the evidence** — no black-box scores.
- **No LLM required for scoring.** The formula is entirely deterministic.

### 11.3 Weight Policy

- Weights are **pilot defaults**.
- Weights may be tuned in v2.12 based on pilot results and founder feedback.
- Any weight change must be documented in a decision record.
- The scoring model version (`pain_cluster_scoring_v1_pilot`) distinguishes pilot weights from future tuned weights.

---

## 12. Scoring Component Definitions

### 12.1 `pain_explicitness` (weight: 0.25)

**Definition:** How explicitly the evidence describes a real, specific, concrete pain attributable to an identifiable actor.

| Score | Criteria | Example |
|-------|----------|---------|
| 0.0 | No pain expressed; announcement, promotion, meta-discussion | "We just raised $10M!" |
| 0.3 | Vague frustration without specifics | "Devtools are broken these days" |
| 0.5 | Pain mentioned but actor/workflow/object unclear | "Debugging is hard" (who? what?) |
| 0.7 | Clear pain with actor and workflow; object partially clear | "Data scientists spend hours cleaning data manually" |
| 0.9 | Very explicit: actor + workflow + object + specific pain verb all clear; workaround described | "We (data engineers) spend 10+ hours/week writing custom scripts to validate data pipelines because existing tools don't catch schema drift" |
| 1.0 | As 0.9 plus cost quantified or specific consequence stated | "We lost $50K last quarter because our data pipeline silently corrupted 3% of records and we had no way to detect it" |

### 12.2 `recurrence` (weight: 0.20)

**Definition:** How many distinct evidence items express the same or similar pain. Normalized from raw count.

**Normalization:**
```
recurrence_score = min(1.0, raw_recurrence_count / 5.0)
if source_diversity >= 2:
    recurrence_score = min(1.0, recurrence_score * 1.15)
```

| Raw Count | source_diversity=1 | source_diversity>=2 |
|-----------|-------------------|---------------------|
| 1 | 0.20 | 0.23 |
| 2 | 0.40 | 0.46 |
| 3 | 0.60 | 0.69 |
| 4 | 0.80 | 0.92 |
| 5+ | 1.00 | 1.00 |

### 12.3 `business_cost` (weight: 0.15)

**Definition:** Estimated cost of the pain to the actor: time lost, money spent, opportunity cost, operational drag.

| Score | Criteria | Example |
|-------|----------|---------|
| 0.0 | No cost implied; purely aesthetic or preference | "I wish the UI was prettier" |
| 0.3 | Minor inconvenience; low time cost | "It's slightly annoying to click three buttons" |
| 0.5 | Moderate cost; time wasted, workaround needed | "I spend 2 hours/week on manual workarounds" |
| 0.7 | Significant cost; clear time/money impact | "Our team of 5 spends 20% of sprint on this" |
| 0.9 | High cost; quantified money loss, compliance risk, customer impact | "We pay $2K/month for a tool just to work around this" |
| 1.0 | Critical cost; existential business risk, regulatory violation | "We cannot launch without solving this; it's a compliance blocker" |

### 12.4 `icp_fit` (weight: 0.15)

**Definition:** How well the pain matches the founder's Ideal Customer Profile and domain preferences. This is the **most subjective** component and is primarily set during founder review.

| Score | Criteria |
|-------|----------|
| 0.0 | Outside ICP entirely (wrong domain, wrong customer type) |
| 0.3 | Tangential to ICP; adjacent domain or customer |
| 0.5 | Partial ICP match; right domain but wrong customer or vice versa |
| 0.7 | Strong ICP match; right domain, right customer type, right problem category |
| 0.9 | Direct ICP match; this is exactly the kind of pain the founder targets |
| 1.0 | Core ICP match; confirmed by founder as top-priority domain |

**Default:** `icp_fit` defaults to 0.5 (neutral) before founder review. The founder can adjust this during review, which feeds back into scoring.

### 12.5 `source_reliability` (weight: 0.10)

**Definition:** Historical signal quality of the source(s) contributing to this cluster.

For single-source clusters: use the source's reliability prior (see Section 15).
For multi-source clusters: weighted average of source reliability priors, weighted by evidence count per source.

| Score | Criteria |
|-------|----------|
| 0.0 | Known noise source; no useful signals historically |
| 0.3 | Low reliability; mostly noise with rare signal |
| 0.5 | Moderate reliability; mixed signal and noise |
| 0.7 | Good reliability; mostly signal, manageable noise |
| 0.9 | High reliability; curated or inherently high-signal source |
| 1.0 | Perfect reliability (reserved for founder-verified sources) |

### 12.6 `freshness` (weight: 0.10)

**Definition:** Recency of the evidence. Decays with age.

**Formula:**
```
age_days = (now - oldest_evidence_created_at).days
if age_days <= 7:
    freshness = 1.0
elif age_days <= 30:
    freshness = 1.0 - (age_days - 7) / 23 * 0.4   # decays from 1.0 to 0.6 over days 7-30
elif age_days <= 90:
    freshness = 0.6 - (age_days - 30) / 60 * 0.3   # decays from 0.6 to 0.3 over days 30-90
else:
    freshness = max(0.1, 0.3 - (age_days - 90) / 270 * 0.2)  # decays from 0.3 to 0.1 over days 90-360
```

If the cluster has evidence with mixed ages, use the **newest** evidence's `created_at` for `freshness`. Pain that is still being reported recently is fresher than pain only reported long ago.

### 12.7 `actionability` (weight: 0.05)

**Definition:** Can a product or service realistically address this pain? Is there a plausible solution?

| Score | Criteria | Example |
|-------|----------|---------|
| 0.0 | Completely unaddressable (law of physics, impossible constraint) | "We need time travel to fix this" |
| 0.3 | Extremely hard to address; requires fundamental breakthrough | "We need AGI to solve this" |
| 0.5 | Addressable but complex; requires significant R&D or integration | "Need a new database engine" |
| 0.7 | Realistically addressable with known technology | "Need a SaaS tool that does X" |
| 0.9 | Clearly addressable; existing solutions could be adapted | "Need a better CI/CD dashboard — existing tools prove demand" |
| 1.0 | Trivially addressable; obvious product/market fit | "Need a simple converter between format A and B" |

### 12.8 `noise_risk` (weight: -0.20)

**Definition:** Estimated probability this cluster is noise (as defined in Section 10).

This is a **penalty** component — it subtracts from the overall score. High noise risk directly suppresses the cluster's final score.

| Score | Criteria |
|-------|----------|
| 0.0 | No noise indicators present; clean signal |
| 0.5 | Moderate noise indicators; some suspicious patterns |
| 1.0 | Certain noise; cluster should be rejected |

---

## 13. Source Reliability Defaults

### 13.1 Initial Source Reliability Priors

These are the pilot default reliability priors for each source type. They inform the `source_reliability` scoring component.

| Source | `source_type` | Reliability Prior | Rationale |
|--------|---------------|-------------------|-----------|
| **GitHub Issues** | `issue_tracker` | **0.78** | Strong for technical/integration pain; explicit bug reports and feature requests; repo allowlist filters noise. Weaker for general market pain (developers are not always representative of end-users). |
| **Hacker News** | `discussion` | **0.72** | Strong for founder/dev/community pain; "Ask HN" and comment threads surface genuine frustrations. High noise risk from flamewars, launch announcements, and meta-discussion. |
| **Stack Exchange / Stack Overflow** | `qa` | **0.62** | Strong for recurring technical "how do I" pain. Weaker as business pain signal (questions are solution-seeking, not necessarily pain-expressing). Included only if pilot adds Stack Exchange. |
| **Product Hunt** | `product_launch` | **Excluded from pilot** | Solution-pattern source, not direct pain source. Deferred to v2.14+. |
| **pimenov.ai** | `curated_context` | **Excluded from pilot** | Expert/context source, not direct pain source. Deferred to context/intelligence layer. |

### 13.2 Reliability Prior Tuning

- These priors are pilot defaults.
- Source reliability may be adjusted based on pilot results:
  - If GitHub Issues produces consistently high-signal pain → increase prior.
  - If HN produces mostly noise → decrease prior.
  - Founder review decisions inform reliability tuning in v2.12.
- Reliability priors are stored in configuration, not hardcoded (subject to v2.12 implementation).

### 13.3 Multi-Source Reliability

For clusters with evidence from multiple sources:

```
source_reliability = sum(reliability_prior[source_type] * evidence_count[source_type]) / total_evidence_count
```

Weighted average by evidence count. A cluster with 3 HN items and 2 GitHub Issues:

```
source_reliability = (0.78 * 2 + 0.72 * 3) / 5 = (1.56 + 2.16) / 5 = 0.744
```

---

## 14. Cluster Status Lifecycle

### 14.1 Status Definitions

| Status | Meaning | Transition Trigger |
|--------|---------|-------------------|
| `new` | Cluster just created; not yet reviewed | Automatic on creation |
| `accepted` | Cluster reviewed and accepted as valid pain | Founder review: PROMOTE |
| `weak` | Cluster has some signal but insufficient evidence | Automatic if score < promotion threshold OR founder review: PARK |
| `noise` | Cluster is noise, not real pain | Automatic if noise_risk >= 0.80 OR founder review: KILL (with noise reason) |
| `needs_more_evidence` | Plausible pain but too few evidence points | Founder review: NEEDS_MORE_EVIDENCE |
| `promoted_to_opportunity` | Cluster has been promoted to opportunity candidate | Automatic or manual promotion after passing thresholds |
| `parked` | Interesting but not now; revisit later | Founder review: PARK |
| `killed` | Not useful; documented reason | Founder review: KILL with `KillReason` |

### 14.2 Status Transition Diagram

```
                    ┌─────────┐
                    │   new   │
                    └────┬────┘
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
     ┌──────────┐  ┌──────────┐  ┌──────────┐
     │ accepted │  │  noise   │  │   weak   │
     └────┬─────┘  └──────────┘  └────┬─────┘
          │                           │
          ▼                           ▼
┌──────────────────┐         ┌──────────────────┐
│ promoted_to_     │         │ needs_more_      │
│ opportunity      │         │ evidence         │
└──────────────────┘         └────────┬─────────┘
                                      │
                            ┌─────────┼─────────┐
                            ▼         ▼         ▼
                      ┌──────────┐ ┌──────┐ ┌────────┐
                      │ accepted │ │ weak │ │ parked │
                      └──────────┘ └──────┘ └────────┘
```

Any status can transition to `killed` with a documented reason.

### 14.3 Automatic Status Assignment

| Condition | Status |
|-----------|--------|
| `noise_risk >= 0.80` | `noise` |
| `overall < 0.30` AND `recurrence < 2` | `weak` |
| `overall < 0.50` AND `noise_risk >= 0.50` | `noise` |
| All other new clusters | `new` (awaiting review) |

Automatic status assignment is **advisory only** — founder review can override any automatic status.

---

## 15. Promotion Rules to Opportunity Candidate

### 15.1 Promotion Thresholds

A PainCluster **may** be promoted to an opportunity candidate when:

| Gate | Threshold | Description |
|------|-----------|-------------|
| **Score** | `overall >= 0.70` | Cluster score meets promotion threshold |
| **Evidence** | At least 1 `primary_pain` evidence item | At least one credible evidence item directly expressing the pain |
| **Decomposition** | Actor, workflow, and object are all identifiable (not "unknown") | The pain is specific enough to form an opportunity hypothesis |
| **Noise** | `noise_risk < 0.50` | Noise risk is below the noise threshold |
| **Traceability** | Every evidence item has a real `source_url` | Source URL traceability is clean |

### 15.2 Score Tiers

| Overall Score | Tier | Recommended Action |
|--------------|------|--------------------|
| >= 0.70 | **Candidate** | Eligible for opportunity framing; promoter review |
| 0.50–0.69 | **Weak / Needs Evidence** | Not eligible for promotion; mark `needs_more_evidence` or `weak` |
| < 0.50 | **Noise / Park** | Likely noise or insufficient; mark `noise` or `parked` |
| Any score with noise_risk >= 0.80 | **Noise** | Mark `noise` regardless of overall score |

### 15.3 Founder Override

The founder can override any automatic promotion decision:

- **PROMOTE** a cluster with `overall < 0.70` if the founder sees value.
- **PARK** a cluster with `overall >= 0.70` if timing is wrong.
- **KILL** any cluster for any reason (documented with `KillReason`).
- **NEEDS_MORE_EVIDENCE** for plausible but thin clusters.

Founder decisions feed back into scoring (Section 16).

### 15.4 Promotion Is Not Automatic

PainCluster promotion to opportunity candidate requires **explicit founder action** (or explicit founder-approved automation). The system does not autonomously promote clusters. This preserves the advisory-only contract.

---

## 16. Founder Review Integration

### 16.1 Founder Decision Statuses

Every PainCluster must receive one of these founder decisions:

| Status | Meaning | Effect on Cluster |
|--------|---------|-------------------|
| `PROMOTE` | Move forward: pain is real, cluster is accepted, candidate for opportunity framing | `status → accepted` or `promoted_to_opportunity` |
| `PARK` | Interesting but not now; revisit later | `status → parked`; set revisit trigger |
| `KILL` | Not useful; document `KillReason` | `status → killed`; document why the pain cluster died |
| `NEEDS_MORE_EVIDENCE` | Plausible but insufficient; request additional evidence | `status → needs_more_evidence`; trigger additional collection |
| `REVISIT_LATER` | Possibly relevant in future; set revisit trigger | `status → parked` with revisit date |

### 16.2 Feedback Loop

Founder decisions feed back into the scoring system:

| Founder Action | Feedback Mechanism |
|----------------|-------------------|
| **KILL due to noise** | Adjust `noise_risk` prior for the source type; identify noise categories |
| **KILL due to wrong ICP** | Adjust `icp_fit` calibration; refine ICP definition |
| **PROMOTE** | Validate scoring weights; confirm `pain_explicitness` and `business_cost` assessments |
| **PARK** | No score adjustment; cluster preserved for later |
| **NEEDS_MORE_EVIDENCE** | Trigger additional collection from under-represented sources |

### 16.3 Scoring Calibration from Founder Feedback

After multiple founder decisions:
- Pattern in KILL decisions → inform `noise_risk` calibration in v2.12.
- Pattern in PROMOTE decisions → inform `icp_fit` tuning in v2.12.
- Source quality assessment → inform `source_reliability` priors in v2.12.
- Mark clusters as useful/not useful to build a labeled dataset for future scoring improvements.

### 16.4 `KillReason` Requirement

When a cluster is killed, the `KillReason` must explain **why the idea died**, not just label it. Per OOS rules:

```
KillReason must explain why the idea died, not just label it.
```

Good: "All three evidence items are self-promotion from the same author; no genuine user pain."
Bad: "Noise."

---

## 17. Cluster Deduplication and Merge Policy

### 17.1 Exact Duplicate Clusters

Two clusters are **exact duplicates** when they have the same `cluster_id` (same normalized actor + workflow + object + pain_pattern).

**Policy:** This should not happen in normal operation (identity is deterministic). If it does (e.g., from a bug or manual creation), merge immediately: combine evidence lists, recalculate all metrics, retain the older `cluster_id`.

### 17.2 Near-Duplicate Pain Patterns

Two clusters are **near duplicates** when their pain patterns are semantically equivalent but differ in normalization (e.g., slightly different wording, different case, synonym substitution).

**Detection (for later implementation):**
- Compare normalized pain patterns with fuzzy matching (e.g., token-set similarity >= 0.85).
- Same actor AND same object but slightly different workflow or pain_verb phrasing.
- Evidence overlap: if two clusters share evidence items, they are likely the same pain.

**Merge Policy:**
- Near-duplicate clusters should be **merged** into one cluster.
- The merge must be **traceable** — the `notes` field records: `"merged_from: [cluster_id_1, cluster_id_2]"`.
- Evidence from both clusters is combined.
- The merged cluster uses the identity of the cluster with more evidence (or the older cluster if tied).
- **No silent merges without traceability.**

### 17.3 Merge Candidate Rules

| Condition | Action |
|-----------|--------|
| Same `cluster_id` | Auto-merge (exact duplicate) |
| Token-set similarity >= 0.85 on pain_pattern | Flag as `merge_candidate`; founder review |
| Same actor + same object + same pain_verb | Flag as `merge_candidate`; founder review |
| Shared evidence items | Flag as `merge_candidate`; founder review |

### 17.4 Retain Evidence Provenance

After a merge, every evidence item retains its original `evidence_id`, `source_id`, `source_type`, `source_url`, `created_at`, and `fetched_at`. The merge combines lists; it does not lose provenance.

---

## 18. Artifact Location and Schema Sketch

### 18.1 Proposed Artifact Paths

```
artifacts/discovery/
├── pain_cluster_index.json                        ← index of all pain cluster runs
└── pain_clusters/
    └── <discovery_run_id>/
        ├── pain_clusters.json                     ← all clusters from one discovery run
        └── ...
```

### 18.2 Top-Level Artifact Sketch (`pain_clusters.json`)

```json
{
  "artifact_type": "pain_clusters",
  "schema_version": "1.0.0",
  "discovery_run_id": "discovery_run_2026-05-12_a1b2c3d4",
  "created_at": "2026-05-12T10:00:00Z",
  "clusters": [
    {
      "cluster_id": "pc_a1b2c3d4e5f6a7b8",
      "actor": "developer",
      "workflow": "AI agent debugging",
      "object": "multi-step agent workflows",
      "pain_verb": "hard to debug / unreliable",
      "pain_pattern": "developers cannot reliably debug AI agent workflows because multi-step agent execution is hard to trace and reproduce",
      "source_evidence_list": [ ],
      "source_diversity": 2,
      "recurrence": 5,
      "business_relevance": 0.75,
      "noise_risk": 0.15,
      "representative_quotes_or_excerpts": [ ],
      "linked_candidate_signals": [ ],
      "linked_opportunity_candidates": [ ],
      "created_at": "2026-05-12T10:00:00Z",
      "updated_at": "2026-05-12T10:00:00Z",
      "status": "new",
      "scoring": { },
      "notes": ""
    }
  ],
  "scoring_summary": {
    "clusters_total": 5,
    "clusters_candidate": 2,
    "clusters_weak": 2,
    "clusters_noise": 1,
    "score_distribution": {
      "min": 0.12,
      "max": 0.82,
      "median": 0.54,
      "mean": 0.50
    }
  },
  "validation_summary": {
    "clusters_passed": 5,
    "clusters_failed": 0,
    "clusters_warned": 1,
    "validation_passed": true
  }
}
```

### 18.3 Pain Cluster Index (`pain_cluster_index.json`)

```json
{
  "artifact_type": "pain_cluster_index",
  "schema_version": "1.0.0",
  "runs": [
    {
      "discovery_run_id": "discovery_run_2026-05-12_a1b2c3d4",
      "created_at": "2026-05-12T10:00:00Z",
      "cluster_count": 5,
      "artifact_path": "artifacts/discovery/pain_clusters/discovery_run_2026-05-12_a1b2c3d4/pain_clusters.json",
      "status": "complete"
    }
  ]
}
```

### 18.4 Implementation Note

This section defines the proposed artifact format for later implementation. **No artifact generation code, no artifact files, and no runtime behavior are authorized by this contract.** The paths and schema are advisory for the implementation phase.

---

## 19. Validation Rules

### 19.1 Fail Rules (Blocking Errors)

A PainCluster that fails any of these rules is invalid and must be rejected:

| # | Rule | Severity |
|---|------|----------|
| VF1 | `cluster_id` is missing or empty | Error |
| VF2 | `actor` is missing, empty, or "unknown" | Error |
| VF3 | `workflow` is missing, empty, or "unknown" | Error |
| VF4 | `object` is missing, empty, or "unknown" | Error |
| VF5 | `pain_pattern` is missing or empty | Error |
| VF6 | `source_evidence_list` is empty (no evidence) | Error |
| VF7 | Any evidence entry has missing or empty `source_url` | Error |
| VF8 | Any evidence entry has a placeholder URL (`urn:oos:*` or similar) | Error |
| VF9 | Any evidence entry has `source_url` not matching `http(s)://` scheme | Error |
| VF10 | `scoring.overall` is outside 0.0–1.0 | Error |
| VF11 | Any `scoring` component is outside 0.0–1.0 | Error |
| VF12 | `scoring.overall` does not match the formula result with the given components | Error |
| VF13 | `source_diversity` does not match distinct source types in evidence list | Error |
| VF14 | `recurrence` does not match length of `source_evidence_list` | Error |
| VF15 | `created_at` or `updated_at` is missing or not valid ISO 8601 | Error |
| VF16 | `status` is not a valid status value | Error |

### 19.2 Warn Rules (Non-Blocking)

A PainCluster that triggers these rules is retained but flagged:

| # | Rule | Severity |
|---|------|----------|
| VW1 | `source_diversity == 1` (single-source only) | Warning |
| VW2 | `noise_risk >= 0.60` (high noise risk) | Warning |
| VW3 | All evidence older than 90 days (stale cluster) | Warning |
| VW4 | `business_relevance < 0.30` (low business relevance) | Warning |
| VW5 | `representative_quotes_or_excerpts` is empty (missing excerpts) | Warning |
| VW6 | No evidence entry has `contribution_to_cluster: primary_pain` | Warning |
| VW7 | `linked_candidate_signals` is empty (evidence-only cluster, no extracted signals) | Warning |
| VW8 | `icp_fit` is exactly 0.5 (default, not founder-reviewed) | Warning |

### 19.3 Pass Conditions

A PainCluster passes validation when:
- All required fields are present and non-empty.
- All fail rules pass.
- Warn rules may be triggered but do not block validation.

---

## 20. Pilot Success/Failure Connection

### 20.1 Expected Cluster Volume

Per the pilot success criteria defined in [`operational_discovery_pilot_reorientation_v2_11.md`](../decisions/operational_discovery_pilot_reorientation_v2_11.md) Section 11:

| Metric | Expected Range | PainCluster Role |
|--------|---------------|-----------------|
| Raw evidence items | 50–150 | Source data feeding clusters |
| Candidate signals | 10–30 | Linked to clusters via `linked_candidate_signals` |
| Pain clusters | **3–7** | **Primary deliverable of this contract** |
| Opportunity candidates | 3–5 | Formed from top-scoring clusters |
| Ideas worth validation | 1–2 | Ultimate pilot goal |

### 20.2 Success Looks Like

- 3–7 PainClusters with clear actor/workflow/object decomposition.
- At least 2 clusters with `source_diversity >= 2` (cross-source validation).
- At least 1–2 clusters scoring `overall >= 0.70` (candidate tier).
- Founder review surfaces real, specific business pains worth investigating.
- Clusters feel like genuine pain patterns, not abstract categories.

### 20.3 Failure Looks Like

- Clusters are banal ("people want faster software", "AI is changing everything").
- Clusters are abstract categories, not specific pains.
- 90%+ of clusters have `noise_risk >= 0.60`.
- No cluster achieves `source_diversity >= 2`.
- Founder review becomes manual trash sorting with no learning feedback.
- Pain decomposition fields are vague or generic across all clusters.

### 20.4 Connection to Go/No-Go Decision (v2.13)

PainCluster quality directly informs the v2.13 Go/No-Go decision:
- If PainClusters surface real, specific, founder-validated pains → **Go** for source expansion.
- If PainClusters are mostly noise, banal, or unactionable → **No-Go** or pipeline fix required.

---

## 21. Non-Goals

This contract explicitly **excludes**:

| Non-Goal | Rationale |
|----------|-----------|
| Implementing PainCluster code (`src/oos/pain_cluster.py` or similar) | Requires later roadmap item and founder approval |
| Changing existing `ClusterSynthesis` or `SemanticCluster` code | PainCluster is additive, not replacement |
| Changing existing `CandidateSignal` extraction pipeline | PainCluster reads, does not modify |
| Changing existing signal scoring (`signal_scoring.py`) | PainCluster scoring is cluster-level, not signal-level |
| LLM-based clustering or scoring | All scoring is deterministic; no LLM calls |
| Live source fetching | Not in scope for contract definition |
| Automatic opportunity promotion | Requires explicit founder action |
| Adding new sources beyond HN + GitHub Issues + optional Stack Exchange | Deferred to v2.14+ |
| Replacing founder review | Founder review is mandatory and preserved |
| Database or persistent server architecture | File-system artifacts only |
| UI or dashboard work | Not in scope |
| Generating artifacts, fixtures, or test data | Implementation concern |
| Running the pilot | Item 9 (Pilot Run Design) covers operational design |

---

## 22. Decision

**v2.11 item 8 defines the PainCluster contract and scoring formula only.**

- No PainCluster implementation is authorized by this item.
- No source code, tests, scripts, or artifacts are modified.
- No runtime behavior is changed.
- The contract defines the artifact schema, field definitions, scoring formula, validation rules, status lifecycle, and promotion policy.
- Implementation of PainCluster creation, scoring computation, artifact persistence, and integration into the weekly run requires later roadmap items and explicit founder approval.
- Weights are pilot defaults and may be tuned in v2.12 based on founder feedback.

---

## 23. Self-Audit

| Question | Answer |
|----------|--------|
| Did this avoid implementation? | **Yes.** Contract/advisory only. No `.py` files modified. |
| Did this avoid source/test changes? | **Yes.** No source, test, script, or example files changed. |
| Did this define all 19 minimum fields? | **Yes.** Section 3.1 defines 19 fields with types and required/optional. |
| Did this define cluster identity rules? | **Yes.** Section 4 defines deterministic cluster_id generation. |
| Did this define pain pattern decomposition? | **Yes.** Section 5 defines actor, workflow, object, pain_verb, pain_pattern with example. |
| Did this define source evidence list? | **Yes.** Section 6 defines 12 evidence entry fields with source_url traceability. |
| Did this define source diversity? | **Yes.** Section 7 defines diversity counting, strength tiers, and over-counting prevention. |
| Did this define recurrence rules? | **Yes.** Section 8 defines what counts, normalization formula, and cross-source bonus. |
| Did this define business relevance rules? | **Yes.** Section 9 defines indicators, non-business indicators, and scoring guidance. |
| Did this define noise risk rules? | **Yes.** Section 10 defines 11 noise categories and scoring guidance. |
| Did this define the explicit scoring formula? | **Yes.** Section 11 defines the formula with weights, constraints, and weight policy. |
| Did this define scoring component definitions? | **Yes.** Section 12 defines all 8 components with 0.0/0.5/1.0 scoring guidance. |
| Did this define source reliability defaults? | **Yes.** Section 13 defines priors for HN, GitHub Issues, Stack Exchange, and excluded sources. |
| Did this define cluster status lifecycle? | **Yes.** Section 14 defines 8 statuses with transition diagram and automatic assignment rules. |
| Did this define promotion rules? | **Yes.** Section 15 defines 5 gates, score tiers, founder override, and no-automatic-promotion policy. |
| Did this define founder review integration? | **Yes.** Section 16 defines decision statuses, feedback loop, and KillReason requirement. |
| Did this define deduplication and merge policy? | **Yes.** Section 17 defines exact duplicates, near-duplicates, merge candidates, and provenance retention. |
| Did this define artifact location and schema sketch? | **Yes.** Section 18 defines proposed paths, top-level schema, and index format. |
| Did this define validation rules? | **Yes.** Section 19 defines 16 fail rules and 8 warn rules. |
| Did this connect to pilot success/failure? | **Yes.** Section 20 defines expected volume, success/failure criteria, and Go/No-Go connection. |
| Did this state non-goals? | **Yes.** Section 21 lists 11 explicit non-goals. |
| Did this state the decision? | **Yes.** Section 22. |
| Did this reference the reorientation decision? | **Yes.** Sections 1, 20, 22. |
| Did this reference `source_url_traceability_contract.md`? | **Yes.** Section 6.2. |
| Did this assess existing clustering/scoring code? | **Yes.** Section 2 maps 7 existing artifacts and their relationship to PainCluster. |
| Did this respect the non-goals? | **Yes.** No implementation, no LLM, no live APIs, no source modification. |

---

*PainCluster Contract and Scoring Formula. v2.11 item 8. Contract finalized / implementation pending.*
