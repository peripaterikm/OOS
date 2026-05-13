# OOS v2.13 — Noise and Quality Analysis Framework

**Title:** OOS v2.13 — Noise and Quality Analysis Framework
**Status:** Draft / operational analysis framework
**Roadmap item:** v2.13 item 9 — Noise and Quality Analysis
**Branch:** `ops/v2-13-operational-pilot-cycle-1`
**Created:** 2026-05-13
**Schema version:** `noise_quality_analysis_framework.v1`

**Based on:**
- [Founder ICP Preference Profile v2.13](founder_icp_preference_profile_v2_13.md) (item 1)
- [Pilot Cycle 1 Brief v2.13](pilot_cycle_1_brief_v2_13.md) (item 2)
- [HN Pilot Query Plan v2.13](hacker_news_pilot_query_plan_v2_13.md) (item 3)
- [GitHub Issues Repo Allowlist and Query Plan v2.13](github_issues_repo_allowlist_query_plan_v2_13.md) (item 4)
- [Pilot Input Preparation Procedure v2.13](pilot_input_preparation_procedure_v2_13.md) (item 5)
- [Pilot Run Procedure v2.13](pilot_run_procedure_v2_13.md) (item 6)
- [Founder Review Protocol v2.13](founder_review_protocol_v2_13.md) (item 7)
- [Pilot Results Report Template v2.13](pilot_results_report_template_v2_13.md) (item 8)
- [PainCluster Contract](../contracts/pain_cluster_contract.md) (v2.11 item 8)
- [Operational Discovery Pilot Run Contract](../contracts/operational_discovery_pilot_run_contract.md) (v2.11 item 9)

---

## 1. Purpose

The purpose of this framework is to determine whether Pilot Cycle 1 quality problems come from:

- **source choice** — are HN and/or GitHub Issues inherently too noisy or too low-signal for the founder's ICP?
- **query design** — are the specific HN query buckets or GitHub repo allowlist producing useful evidence or mostly noise?
- **repo allowlist** — are the selected GitHub repos the right ones for finding business-relevant pain?
- **input quality** — is the raw evidence collected well-formed, traceable, and signal-bearing?
- **signal extraction** — is the candidate signal extractor correctly identifying pain signals from raw evidence?
- **PainCluster assembly** — are clusters specific, meaningful, and cross-source-consolidated?
- **scoring** — does the deterministic scoring formula produce scores that align with founder judgment?
- **founder review package quality** — is the review package structured, navigable, and decision-enabling?
- **true lack of useful opportunity signals** — is there simply no signal in the current source set for the founder's ICP?

This framework is the **analytical bridge** between the Pilot Results Report (item 8) and the Go / Conditional Go / No-Go Decision (item 10). It provides the diagnostic procedures, classification taxonomies, quality thresholds, and tuning recommendations that turn raw pilot observations into actionable decision support.

### 1.1 What This Framework Is

- A structured analytical procedure for diagnosing noise and quality issues in Pilot Cycle 1.
- A noise taxonomy with definitions, examples, likely sources, and recommended responses.
- A set of quality thresholds for interpreting pilot results.
- Source-level, cluster-level, and scoring-level analysis questions.
- A query/repo tuning action catalog.
- A decision-support mapping from analysis findings to v2.14 roadmap direction.

### 1.2 What This Framework Is Not

- A runtime analysis of actual pilot outputs (no pilot data is filled in).
- A pilot run authorization.
- A pilot results report.
- A founder decision artifact.
- A `KillReason` record.
- A portfolio mutation.
- Source code, test, script, or artifact modification.
- A live API call authorization.
- An HN or GitHub query execution.
- A scoring weight change.
- A clustering logic change.

---

## 2. Required Inputs

The following inputs are expected to be available before the noise and quality analysis is performed. All inputs are produced by items 5–8 of this roadmap.

### 2.1 Mandatory Inputs

| # | Input | Format | Source Item | Description |
|---|-------|--------|-------------|-------------|
| 1 | `pilot_results_report_v2_13.md` | Markdown | Item 8 | Aggregated pilot results with all 12 required sections |
| 2 | `source_quality_report.json` | JSON | Item 6 / Item 8 | Per-source quality metrics (signal rate, noise rate, missing URLs, top noise categories) |
| 3 | `source_quality_report.md` | Markdown | Item 6 / Item 8 | Human-readable source quality summary with recommendations |
| 4 | `founder_review_notes_v2_13.md` | Markdown | Item 7 | Structured review notes with decisions, rationales, and quality markers |
| 5 | `founder_review_package.json` | JSON | Item 6 | Structured review package with cluster scores, evidence links, advisory recommendations |
| 6 | `founder_review_package.md` | Markdown | Item 6 | Human-readable review package |
| 7 | `pain_clusters.json` | JSON | Item 6 | Full cluster data: pain patterns, scores, evidence lists, source diversity |
| 8 | `candidate_signals.json` | JSON | Item 6 | Full candidate signal list with scores and traceability |
| 9 | `validation_summary.json` | JSON | Item 6 | Pipeline validation: format checks, traceability pass/fail, source scope compliance |
| 10 | `pilot_run_manifest.json` | JSON | Item 6 | Run metadata: parameters, counts, approvals, limitations |

### 2.2 Optional Deeper-Inspection Inputs

| # | Input | Format | Description |
|---|-------|--------|-------------|
| 11 | `raw_evidence.json` | JSON | Original raw evidence for traceability or content verification of specific items |
| 12 | `duplicates.json` | JSON | Records of detected and merged duplicate evidence items |
| 13 | `input_manifest.json` or `input_manifest.md` | JSON/Markdown | Manifest describing input package contents, mode, counts, approvals |
| 14 | `approval_record.json` or `approval_record.md` | JSON/Markdown | Record of all approvals granted for this pilot input |

### 2.3 Reference Documents (Read-Only)

| # | Document | Purpose |
|---|----------|---------|
| R1 | [Founder ICP Preference Profile v2.13](founder_icp_preference_profile_v2_13.md) | ICP definitions, excluded markets, relevance signals, noise definitions, review rubric |
| R2 | [Pilot Cycle 1 Brief v2.13](pilot_cycle_1_brief_v2_13.md) | Success/failure criteria, timebox, decision outcomes |
| R3 | [HN Pilot Query Plan v2.13](hacker_news_pilot_query_plan_v2_13.md) | HN query buckets, collection parameters, noise risk assessments |
| R4 | [GitHub Issues Repo Allowlist and Query Plan v2.13](github_issues_repo_allowlist_query_plan_v2_13.md) | Repo allowlist, issue search logic, selection principles |
| R5 | [Founder Review Protocol v2.13](founder_review_protocol_v2_13.md) | Decision definitions, scoring rubric, review burden assessment |
| R6 | [PainCluster Contract](../contracts/pain_cluster_contract.md) | Scoring formula, component definitions, noise categories, promotion thresholds |

---

## 3. Analysis Dimensions

The noise and quality analysis must examine at least the following nine dimensions. Each dimension includes specific questions to answer and methods for answering them.

### 3A. Source Quality

**Questions:**
- Was HN useful or noisy overall? What proportion of HN evidence produced accepted signals vs. weak/noise?
- Was GitHub Issues useful or noisy overall? What proportion of GitHub evidence produced accepted signals vs. weak/noise?
- Did one source dominate the accepted signal pool? Did one source dominate the noise pool?
- Did source diversity (HN + GitHub cross-source evidence) produce stronger clusters than single-source clusters?
- Did either source produce systematically broken traceability (missing/placeholder URLs)?

**Method:**
- Cross-reference `source_quality_report.json` per-source metrics against founder review decisions.
- For each source, compute: `useful_signal_rate = (accepted_signals + founder_PROMOTE) / total_records`.
- For each source, compute: `noise_rate = (noise_signals + founder_KILL_with_noise_rationale) / total_records`.
- Compare cluster scores for single-source vs. cross-source clusters.

### 3B. Query Quality

**Questions (HN):**
- Which HN query buckets (A through H, per the HN Query Plan) produced useful evidence?
- Which buckets produced hype, flamewar, self-promotion, or launch announcements?
- Did "Ask HN" queries outperform "Show HN" / "Launch HN" queries for pain signal quality?
- Did comment-based evidence provide better pain signal than story-based evidence?
- Should any HN query bucket be killed, capped, or revised for Cycle 2?

**Questions (GitHub Issues):**
- Which GitHub query templates (per repo) produced issues with clear actor/workflow/object pain?
- Which repos produced implementation noise (one-off bugs, feature requests without business pain, bot activity)?
- Did any repo dominate the evidence pool in a way that skewed results?
- Were pull requests, bot issues, and stale issues properly excluded?
- Should any repo be removed from the allowlist for Cycle 2?

**Method:**
- Cross-reference `source_quality_report.json` per-query-bucket and per-repo metrics against founder review decisions.
- For each HN bucket, tag evidence by content type (Ask HN / Show HN / Launch HN / comment) and compute signal rate.
- For each GitHub repo, tag issues by apparent type (bug, feature request, workflow pain, integration pain) and compute signal rate.

### 3C. Evidence Quality

**Questions:**
- Is the actor/workflow/object decomposition clear for each evidence item?
- Is the pain explicit, or is it implied/vague?
- Is business cost visible (time, money, risk)?
- Is there evidence of repeated workaround behavior?
- Is every `source_url` traceable to a real `http(s)://` URL?
- What is the `low_text_context` rate (evidence items with insufficient body text to extract a signal)?

**Method:**
- Audit a random sample of evidence items (at least 20, or all if fewer than 20) for actor/workflow/object clarity.
- Count evidence items where `pain_explicitness` was scored < 0.5.
- Count evidence items with `business_cost` scored < 0.3.
- Verify `source_url` traceability via `validation_summary.json` traceability section.
- Count evidence items flagged with `low_text_context` or equivalent quality flag.

### 3D. Signal Quality

**Questions:**
- What is the ratio of accepted signals vs. weak signals vs. noise signals?
- Are there false positives (items scored as accepted but founder-reviewed as KILL with noise rationale)?
- Are there false negatives (items scored as weak/noise but founder-reviewed as PROMOTE or NEEDS_MORE_EVIDENCE)?
- Is the weak signal pool too large relative to accepted signals?
- Were useful signals missed or overfiltered by the extraction pipeline?

**Method:**
- Compute `precision = founder_PROMOTE / system_accepted_signals` (among reviewed items).
- Compute `recall = founder_PROMOTE / (founder_PROMOTE + founder_false_negatives)` if discoverable.
- Compute `false_positive_rate = founder_KILL_with_noise_rationale / system_accepted_signals`.
- Compare system-assigned signal quality (accepted/weak/noise) against founder review markers (interesting/banal/unclear/actionable).

### 3E. PainCluster Quality

**Questions:**
- Are clusters specific (clear actor + workflow + object + pain_verb) or generic (vague domain-level grouping)?
- Were duplicate pains merged correctly (same pain across sources became one cluster)?
- Were unrelated pains merged incorrectly (different pains forced into one cluster)?
- Are HN + GitHub cross-source clusters meaningful (same real pain observed in both sources)?
- Is source diversity (>= 2 distinct source types) a useful signal of cluster quality?
- Is recurrence (multiple distinct evidence items for the same pain) meaningful or artificial?

**Method:**
- For each cluster, rate specificity on a 3-point scale: `specific` (clear actor/workflow/object), `moderate` (some dimensions clear), `generic` (vague domain grouping).
- Check near-duplicate clusters: are there clusters with token-set similarity >= 0.85 on pain_pattern that should have been merged?
- Check over-merged clusters: do any clusters contain evidence that describes different pains?
- Compare cross-source cluster scores and founder decisions against single-source cluster scores and founder decisions.
- Check if recurrence counts are inflated by comments on the same thread or cross-posts.

### 3F. Scoring Quality

**Questions:**
- Did high-scoring clusters (overall >= 0.70) match founder judgment (PROMOTE)?
- Did low-scoring clusters (overall < 0.50) match founder judgment (KILL or PARK)?
- Were there over-promotions (high system score, founder KILL)?
- Were there over-kills (low system score, founder PROMOTE)?
- Is `business_relevance` weighted correctly — does it differentiate useful from banal?
- Is `noise_risk` weighted correctly — does it suppress truly noisy clusters?
- Is `icp_fit` useful as a scoring component, or is it too neutral (default 0.5) to differentiate?

**Method:**
- Build a confusion matrix: system score tier (high >= 0.70 / medium 0.50–0.69 / low < 0.50) vs. founder decision (PROMOTE / NEEDS_MORE_EVIDENCE / PARK / KILL / REVISIT_LATER).
- For each over-promotion (high score, founder KILL), identify which scoring component(s) failed.
- For each over-kill (low score, founder PROMOTE), identify which scoring component(s) were underweighted.
- Check distribution of `icp_fit` scores: if >80% are at the default 0.5, the component is not differentiating.
- Check distribution of `noise_risk` scores: if noise_risk is uniformly low despite real noise, the noise detection is failing.

### 3G. Opportunity Candidate Quality

**Questions:**
- Are opportunity candidates specific (named buyer, named pain, named workflow) or abstract ("an AI-powered platform for developers")?
- Is the buyer clear and reachable?
- Is the suggested validation action clear and feasible in 1–2 weeks?
- Is the business model plausible?
- Are candidates too devtools-heavy relative to founder preferences?
- Are candidates too far from founder-preferred ICPs and domains?

**Method:**
- For each opportunity candidate, rate specificity on a 3-point scale: `specific` (buyer + problem + validation path clear), `moderate`, `abstract` (vague problem statement, no clear buyer).
- Cross-reference candidates against founder ICP (Sections 3–5 of the ICP profile): which ICP does each candidate serve?
- Cross-reference candidates against Pilot Cycle 1 focus themes (F-1 through F-7): does each candidate fall within the focus?
- Check if the suggested validation action is actionable within 1–2 weeks.

### 3H. Founder Review Burden

**Questions:**
- How much time did the founder spend on review? Did it exceed the target (60–120 minutes) or the maximum (3 hours)?
- Was the review package clear and navigable, or did the founder have to hunt for information?
- Were evidence links useful — could the founder click through to verify claims?
- Did the founder spend disproportionate time on obvious noise/trash?
- Were the system's recommendation reasons helpful, or did the founder have to override them frequently?
- Was the source quality report helpful in understanding which sources/queries to tune?

**Method:**
- Record actual review time from founder review notes.
- Count the number of items where the founder overrode the system recommendation.
- Count the number of items where the founder marked the system recommendation as unhelpful.
- Assess source quality report utility: did the founder reference it during review?
- Identify review friction points from founder notes.

### 3I. Traceability and Operational Reliability

**Questions:**
- Are there any missing `source_url` values in any artifact?
- Are there any placeholder URLs (e.g., `github://...`, `urn:oos:...`)?
- Are there any invalid URLs (unreachable, 404, malformed)?
- Are all expected artifacts present and complete?
- Was the `output_dir` policy followed (explicit caller-provided directory; no default writes)?
- Was the `validation_summary` useful — did it catch real problems before founder review?

**Method:**
- Count missing/placeholder/invalid URLs from `validation_summary.json` traceability section.
- Verify artifact completeness against the pilot run procedure artifact checklist.
- Verify `output_dir` policy compliance from `pilot_run_manifest.json`.
- Check if `validation_summary.is_valid` was `true` before founder review began.

---

## 4. Noise Taxonomy

The following noise categories are defined for classifying evidence items, signals, and clusters that do not represent real, actionable business pain. Each category includes: meaning, examples, likely source, and recommended response.

### 4.1 Noise Category Definitions

#### `generic_ai_hype`

- **Meaning:** Content about AI/LLM trends without specific pain, actor, or workflow. "AI is changing everything" discourse.
- **Examples:** "The future of AI agents in 2026", "Will AGI replace developers?", "AI trends to watch".
- **Likely source:** HN — especially bucket G (broad AI/automation trends) and bucket H (general devtools discussion).
- **Recommended response:** **Filter.** Add `-hype -trends -predictions` qualifiers to broad queries. Cap or kill buckets that produce >50% hype.

#### `self_promotion`

- **Meaning:** Someone promoting their own product, service, or startup without describing a real user pain.
- **Examples:** "Check out my new AI debugging tool!" (Show HN with no pain description), "We just launched our MVP".
- **Likely source:** HN — Show HN and Launch HN content types; some Ask HN. GitHub — rare, but possible in repo README-linked promotional issues.
- **Recommended response:** **Flag.** In HN collection, flag Show HN and Launch HN content with `self_promotion` noise category. In scoring, increase `noise_risk` for items with promotional language patterns.

#### `launch_hype`

- **Meaning:** Product launch announcements with promotional language but no user pain evidence.
- **Examples:** "Announcing FooBar 2.0 — now with AI!", YC launch posts without problem statements.
- **Likely source:** HN — Launch HN, some Show HN.
- **Recommended response:** **Flag and tune query.** Reduce Launch HN collection weight. Apply `launch_hype` flag to items matching launch-announcement patterns.

#### `flamewar_or_meta_discussion`

- **Meaning:** Heated arguments, language wars, meta-commentary about HN/GitHub culture, not constructive pain discussion.
- **Examples:** "Rust vs Go debate with 200 comments", "Why HN is declining", "GitHub is ruined by AI slop".
- **Likely source:** HN — comment threads, especially on controversial posts; bucket H (general discussion).
- **Recommended response:** **Filter.** Exclude items where the primary content is argumentative rather than pain-descriptive. Detect via sentiment extremity and topic drift patterns.

#### `low_text_context`

- **Meaning:** Evidence item with too little body text to extract a meaningful signal — title-only, one-liner, or placeholder content.
- **Examples:** GitHub issue: "It's broken. Fix it." with no description. HN comment: "+1" or "This.".
- **Likely source:** GitHub Issues — especially low-effort bug reports. HN — short, low-effort comments.
- **Recommended response:** **Filter.** Set minimum text length threshold (e.g., >= 100 characters) for signal extraction. Flag items below threshold as `low_text_context` noise.

#### `one_off_bug`

- **Meaning:** A bug affecting one user in one specific, unreproducible context with no broader pain implication.
- **Examples:** "This crashes when I use Python 3.7 on Windows XP with a specific locale setting."
- **Likely source:** GitHub Issues — especially repos with large issue volumes.
- **Recommended response:** **Flag.** Not all one-off bugs are noise, but they should not form clusters. Flag with `one_off_bug` noise category; do not allow single-issue clusters from one-off bugs to become opportunity candidates.

#### `implementation_detail_without_business_pain`

- **Meaning:** Technical discussion about implementation approaches, code style, or architecture preferences without a business pain being described.
- **Examples:** "Should we use Redis or Postgres for this queue?", "Refactor the auth module to use async/await".
- **Likely source:** GitHub Issues — especially feature requests and refactoring proposals. HN — technical deep-dives.
- **Recommended response:** **Flag.** Tag items where the content is technical-implementation-focused with no business cost signal. Exclude from business-relevance scoring.

#### `bot_or_maintenance_noise`

- **Meaning:** Automated dependency updates, bot-generated issues, release chore tasks, CI/CD maintenance.
- **Examples:** Dependabot PRs (should already be excluded by PR filter), "Bump version to 2.3.1", "Update changelog for release".
- **Likely source:** GitHub Issues — unless explicitly excluded by the PR filter and bot exclusion rules.
- **Recommended response:** **Exclude.** Already handled by the GitHub Issues connector's PR exclusion and bot-issue filtering. Verify these exclusions are working in the pilot.

#### `duplicate_or_invalid`

- **Meaning:** Near-duplicate of another evidence item, cross-posted content, or item with invalid/malformed data.
- **Examples:** Same HN post collected via two different queries. GitHub issue cross-referenced in an HN post (legitimate cross-source, not duplicate). Malformed JSON entries.
- **Likely source:** Both HN and GitHub Issues — collection deduplication failures.
- **Recommended response:** **Filter (deduplicate).** Ensure deduplication runs before signal extraction. Flag unresolved duplicates for manual review.

#### `stale_issue`

- **Meaning:** Old GitHub issue with no recent activity, likely already resolved, abandoned, or irrelevant.
- **Examples:** GitHub issue from 2019 with no comments since 2020, closed without resolution.
- **Likely source:** GitHub Issues — especially if closed-issue collection includes old issues.
- **Recommended response:** **Flag.** Apply freshness scoring penalty. Consider excluding issues with no activity in >12 months unless they have clear ongoing relevance.

#### `wishlist_without_pain`

- **Meaning:** Feature request or wishlist item that describes a desired feature without describing a real pain or workflow breakage.
- **Examples:** "It would be cool if this supported Kubernetes", "Add dark mode please".
- **Likely source:** GitHub Issues — feature requests. HN — "I wish there was a tool that..."
- **Recommended response:** **Flag.** Distinguish between pain-driven feature requests ("I can't do X because Y is broken") and wishlist items ("It would be nice if Z existed"). Only pain-driven requests are signal.

#### `hobby_only`

- **Meaning:** Pain in a hobby, personal, or free-tier context with no business or professional implications.
- **Examples:** "My Home Assistant dashboard doesn't look good", "My personal blog's RSS feed is broken".
- **Likely source:** HN — especially Ask HN: personal-project questions. GitHub Issues — personal/hobby repos.
- **Recommended response:** **Filter.** Set `business_relevance = 0.0` for hobby-only contexts. Match against hobby-repo patterns in the GitHub allowlist.

#### `unclear_actor`

- **Meaning:** The evidence describes a pain but the actor (who experiences it) is unidentifiable — "people", "users", "everyone".
- **Examples:** "People want better tools", "Users are frustrated with the current workflow".
- **Likely source:** Both HN and GitHub Issues — vague complaints.
- **Recommended response:** **Flag.** Score `pain_explicitness` <= 0.5 when actor is unidentifiable. Do not promote items with unclear actor to opportunity candidate.

#### `unclear_workflow`

- **Meaning:** The pain is mentioned but the affected workflow or process is not described.
- **Examples:** "Development is too slow", "The tooling is bad".
- **Likely source:** Both HN and GitHub Issues — vague complaints.
- **Recommended response:** **Flag.** Score `pain_explicitness` <= 0.5 when workflow is unidentifiable. Do not promote items with unclear workflow to opportunity candidate.

#### `unclear_buyer`

- **Meaning:** A pain is described but there is no identifiable buyer who would pay to solve it.
- **Examples:** Pain affecting open-source maintainers who don't control budgets. Pain affecting students. Pain affecting hobbyists.
- **Likely source:** Both sources.
- **Recommended response:** **Flag.** Score `business_relevance` <= 0.3 when no buyer is identifiable. Do not promote to opportunity candidate without a buyer hypothesis.

#### `no_business_cost`

- **Meaning:** Pain is described but there is no cost signal — no time lost, money spent, revenue at risk, or compliance threat.
- **Examples:** "It's slightly annoying", "I wish this was prettier", "This UX could be improved".
- **Likely source:** Both sources.
- **Recommended response:** **Flag.** Score `business_cost` <= 0.3 when no cost signal is present. Do not count as primary pain evidence.

#### `legal_or_tos_risk`

- **Meaning:** The pain is real but the opportunity involves legal grey areas, Terms of Service violations, or regulatory risk that the founder has explicitly excluded.
- **Examples:** "We scrape competitor pricing and need a better scraper", "We need to bypass YouTube's rate limiting".
- **Likely source:** Both sources.
- **Recommended response:** **Flag and exclude.** Per the founder ICP profile (Section 6 — Excluded Markets, X-12), legally risky opportunities are excluded. Score `icp_fit = 0.0` for legal-risk items.

#### `source_scope_violation`

- **Meaning:** Evidence from a source not in the pilot scope (e.g., Reddit, Product Hunt, X/Twitter) appearing in pilot inputs.
- **Examples:** Reddit post mistakenly collected. Product Hunt launch appearing in HN cross-posts (but the source_id is HN, not PH — this is fine; the violation is only if `source_id` itself is out of scope).
- **Likely source:** Collection pipeline misconfiguration.
- **Recommended response:** **Reject.** Source scope violations are gate failures (G3). Escalate; do not include in analysis.

#### `traceability_failure`

- **Meaning:** Evidence item with missing, placeholder, or invalid `source_url`. Cannot trace back to origin.
- **Examples:** Missing `source_url` field. Placeholder `urn:oos:...` URL. `github://` fallback URL.
- **Likely source:** Collection pipeline or artifact serialization bug.
- **Recommended response:** **Reject.** Traceability failures invalidate the evidence item. Do not include in clusters. Escalate if systemic.

### 4.2 Noise Category Summary Table

| # | Category | Severity | Default Action |
|---|----------|----------|----------------|
| 1 | `generic_ai_hype` | High | Filter from broad queries |
| 2 | `self_promotion` | Medium | Flag; increase noise_risk |
| 3 | `launch_hype` | Medium | Flag; reduce Launch HN weight |
| 4 | `flamewar_or_meta_discussion` | High | Filter; exclude from signal extraction |
| 5 | `low_text_context` | High | Filter; minimum text threshold |
| 6 | `one_off_bug` | Low | Flag; do not form single-issue clusters |
| 7 | `implementation_detail_without_business_pain` | Medium | Flag; score business_relevance=0.0 |
| 8 | `bot_or_maintenance_noise` | High | Exclude entirely |
| 9 | `duplicate_or_invalid` | Medium | Deduplicate or reject |
| 10 | `stale_issue` | Medium | Flag; apply freshness penalty |
| 11 | `wishlist_without_pain` | Medium | Flag; distinguish from pain-driven requests |
| 12 | `hobby_only` | Medium | Score business_relevance=0.0 |
| 13 | `unclear_actor` | Medium | Flag; score pain_explicitness <=0.5 |
| 14 | `unclear_workflow` | Medium | Flag; score pain_explicitness <=0.5 |
| 15 | `unclear_buyer` | Medium | Flag; score business_relevance <=0.3 |
| 16 | `no_business_cost` | Medium | Flag; score business_cost <=0.3 |
| 17 | `legal_or_tos_risk` | High | Exclude; score icp_fit=0.0 |
| 18 | `source_scope_violation` | Critical | Reject; escalate |
| 19 | `traceability_failure` | Critical | Reject; escalate |

---

## 5. Quality Thresholds

The following thresholds interpret pilot results and map them to decision outcomes. These thresholds are applied after the noise and quality analysis dimensions (Section 3) have been examined and the noise taxonomy (Section 4) has been counted.

### 5.1 Excellent

| Indicator | Threshold |
|-----------|-----------|
| Overall noise rate | < 40% of evidence |
| Strong clusters (specific pain, founder PROMOTE) | At least 2 clusters with `overall >= 0.70` AND founder PROMOTE |
| PROMOTE candidates | At least 1–2 ideas worth real validation |
| Traceability | Clean — zero missing/placeholder/invalid URLs |
| Founder review time | Under 90 minutes |
| Scoring-foundation alignment | >= 80% of high-scoring items (>= 0.70) received PROMOTE or NEEDS_MORE_EVIDENCE from founder |
| Cross-source clusters | At least 1 cluster with `source_diversity >= 2` that founder rated useful |

**Interpretation:** The pipeline is working well on the current source set. GO decision is strongly supported. Cautious source expansion planning is appropriate.

### 5.2 Acceptable

| Indicator | Threshold |
|-----------|-----------|
| Overall noise rate | 40–60% of evidence |
| Useful clusters | At least 1 cluster/candidate that founder found worth investigating |
| Diagnosability | Noise and quality issues are diagnosable — specific sources/queries/components can be identified as problems |
| Founder review time | Under 2 hours |
| Scoring-foundation alignment | 60–79% of high-scoring items received PROMOTE or NEEDS_MORE_EVIDENCE |
| Traceability | Minor issues (1–2 missing URLs, isolated, fixable) |

**Interpretation:** The pipeline produces some signal but needs improvement. CONDITIONAL GO is supported. The specific improvements should be scoped in v2.14 Pilot Quality Improvements.

### 5.3 Problematic

| Indicator | Threshold |
|-----------|-----------|
| Overall noise rate | 60–80% of evidence |
| Signal quality | Mostly weak signals; few or no accepted signals |
| Cluster quality | Most clusters are generic/abstract; lack specific actor/workflow/object |
| Founder review burden | High — review time > 2 hours; founder spent disproportionate time on noise |
| Scoring-foundation alignment | 40–59% of high-scoring items received PROMOTE or NEEDS_MORE_EVIDENCE |
| Traceability | Multiple missing/placeholder URLs; systematic pattern |

**Interpretation:** The pipeline has significant quality problems. CONDITIONAL GO with substantial fixes, or NO-GO if fixes cannot be scoped with confidence. Source expansion must not proceed.

### 5.4 Failing

| Indicator | Threshold |
|-----------|-----------|
| Overall noise rate | > 80% of evidence |
| Validatable ideas | Zero — nothing passes the "would I test this?" threshold |
| Traceability | Broken — systematic missing URLs, placeholder URLs, unresolvable sources |
| Scoring accuracy | Systematically wrong — founder overrides >50% of system recommendations |
| Founder review experience | Feels like manual trash sorting; no learning; no useful output |
| Cluster quality | Banal/generic pain clusters ("people want faster software", "AI is changing everything") |
| Opportunity candidates | Abstract, unactionable ("an AI-powered platform for developers", "a better DevOps tool") |

**Interpretation:** The pipeline is not working. NO-GO decision is required. Core Discovery Pipeline Repair must precede any source expansion. Diagnose root causes before reconsidering sources.

---

## 6. Source-Level Analysis

For each source used in Pilot Cycle 1, answer the following questions after examining pilot data.

### 6.1 Hacker News

| # | Question | Data Source | Decision Implication |
|---|----------|-------------|---------------------|
| HN-1 | Which query buckets (A–H) produced useful evidence (>= 1 accepted signal with founder PROMOTE or NEEDS_MORE_EVIDENCE)? | `source_quality_report.json`, `founder_review_notes_v2_13.md` | Keep useful buckets; kill or cap the rest |
| HN-2 | Which query buckets were noise (>50% weak/noise signals, or all items founder KILL)? | Same as HN-1 | Kill or cap noisy buckets |
| HN-3 | Was HN too hype-driven overall? Did AI/LLM hype dominate even useful buckets? | `source_quality_report.json`, noise taxonomy counts | If hype >40%, add hype-filter qualifiers or narrow queries |
| HN-4 | Was HN too devtools-heavy relative to founder preference for SMB/finance/operations ICPs? | Cross-reference HN signals against ICP priority tiers (ICP-1 through ICP-13) | If >80% of HN signals match only ICP-5 (developers building with AI agents), HN is too narrow for the founder's broader ICP |
| HN-5 | Did Ask HN content produce better pain evidence than Show HN or Launch HN? | Compare signal rates by content type | If Ask HN significantly outperforms, increase Ask HN weight and reduce Show HN / Launch HN |
| HN-6 | Did comments produce better pain evidence than stories (original posts)? | Compare signal rates: comments vs. stories | If comments are high-signal, expand comment collection within bounded limits. If comments are noise, exclude or cap. |
| HN-7 | Which content type (Ask HN, Show HN, Launch HN, comment, search result) produced the most noise? | Noise rate per content type | Cap or kill the noisiest content type |
| HN-8 | Should any HN query bucket be killed entirely for Cycle 2? | Per-bucket signal rate < 10% OR per-bucket noise rate > 80% | Kill the bucket |
| HN-9 | Should any HN query bucket be capped to fewer items? | Per-bucket signal rate 10–30% | Cap the bucket to half its current max records |
| HN-10 | Should HN collection be expanded to include new query buckets? | Only if all existing buckets are useful AND the founder wants more HN volume | Not in v2.13; defer to v2.14+ |
| HN-11 | Was HN collection volume within the expected range (per the Pilot Cycle 1 Brief, Section 4: 50–150 total raw evidence)? | `pilot_run_manifest.json`, raw evidence counts | If volume was too low, consider lowering the per-item minimum text threshold or adjusting query terms. If too high, cap more aggressively. |

### 6.2 GitHub Issues

| # | Question | Data Source | Decision Implication |
|---|----------|-------------|---------------------|
| GH-1 | Which repos in the allowlist produced useful pain evidence (>= 1 accepted signal with founder PROMOTE or NEEDS_MORE_EVIDENCE)? | `source_quality_report.json`, `founder_review_notes_v2_13.md` | Keep useful repos |
| GH-2 | Which repos produced implementation noise (>50% items flagged as `implementation_detail_without_business_pain`, `one_off_bug`, or `wishlist_without_pain`)? | Same as GH-1 | Remove or cap noisy repos |
| GH-3 | Did GitHub Issues provide stronger specificity (actor/workflow/object clarity) than HN? | Compare `pain_explicitness` scores HN vs. GitHub | If GitHub Issues are more specific, this informs source weighting for Cycle 2 |
| GH-4 | Were pull requests, bot issues, and stale issues properly excluded? | Count PRs, bot issues, stale issues that passed the exclusion filters | If exclusions failed, fix the GitHub Issues connector before Cycle 2 |
| GH-5 | Did any single repo dominate the evidence pool (>40% of all GitHub evidence)? | Per-repo evidence counts | If one repo dominates, cap its collection weight or broaden the allowlist |
| GH-6 | Did any repo produce evidence that founder consistently KILLed (>= 80% KILL rate)? | Cross-reference repo against founder decisions | Remove the repo from Cycle 2 allowlist |
| GH-7 | Did the repo allowlist miss repos that would have been useful (discovered via HN cross-references or founder notes)? | Founder review notes, cross-source evidence matching | Consider adding to Cycle 2 allowlist |
| GH-8 | Were closed issues useful or mostly noise? | Compare signal rates: open vs. closed issues | If closed issues are mostly noise/stale, exclude closed issues from Cycle 2 |
| GH-9 | Was GitHub Issues collection volume within the expected range? | `pilot_run_manifest.json` | Adjust per-repo caps if volume was too high or too low |
| GH-10 | Should the repo allowlist be expanded with new repos for Cycle 2? | Only if all existing repos are useful AND founder wants more GitHub volume | Not in v2.13; defer to v2.14+ conditional on Go/Conditional Go |

---

## 7. Cluster-Level Analysis

For each top PainCluster (ranked by `overall` score, at minimum the top 5 clusters or all clusters if fewer than 5), answer the following questions.

### 7.1 Per-Cluster Analysis Questions

| # | Question | What to Check | Red Flag |
|---|----------|---------------|----------|
| CL-1 | Was the pain pattern specific? | Actor, workflow, object, and pain_verb are all identifiable and non-generic. | Actor is "people" or "developers" (too broad); workflow is "software development" (too vague). |
| CL-2 | Did the evidence belong together? | All evidence items in `source_evidence_list` describe the same pain or semantically equivalent pains. | Cluster contains a bug report, a feature request, and a launch announcement — these are different things. |
| CL-3 | Was source diversity meaningful? | If `source_diversity >= 2`, do the HN and GitHub evidence items actually describe the same pain from different angles? | HN post is about AI debugging frustration; GitHub issue is about a specific CSS bug. Both are about "debugging" but not the same pain. |
| CL-4 | Was recurrence real or artificial? | Are the distinct evidence items truly from different actors expressing the same pain independently? | All evidence items are comments on the same HN thread from the same 2 users. |
| CL-5 | Was business relevance clear? | Does the cluster's `business_relevance` score align with evidence of cost, buyer, and market? | `business_relevance = 0.7` but no cost signal in any evidence item. |
| CL-6 | Did founder agree with system score? | Compare `overall` score tier (high/medium/low) against founder decision (PROMOTE/PARK/KILL/NEEDS_MORE_EVIDENCE/REVISIT_LATER). | High score (>= 0.70), founder KILL. Or low score (< 0.50), founder PROMOTE. |
| CL-7 | Should the cluster be promoted, split, merged, parked, or killed? | Based on all above, what is the recommended cluster action for Cycle 2? | Document rationale. |

### 7.2 Cluster Action Catalog

| Action | When to Apply | Example |
|--------|---------------|---------|
| **Promote** | Specific pain, clear buyer, founder PROMOTE or strong interest, scoring aligned. | Cluster about "SMB owners cannot reconcile Stripe payouts across multiple bank accounts without manual spreadsheet work" → promote to opportunity candidate. |
| **Split** | Cluster contains two or more distinct pains that were incorrectly merged. | Cluster merges "AI agent debugging is hard" with "CI/CD pipelines are unreliable" — similar domain but different pains. |
| **Merge** | Two clusters describe the same pain but have different `cluster_id` (near-duplicate pain patterns). | Cluster A: "developer / AI agent debugging / multi-step agent workflows / hard to debug". Cluster B: "engineer / debugging AI agents / agent workflows / unreliable". Token-set similarity >= 0.85. |
| **Park** | Pain is specific and real but timing, market, or founder focus is not right now. | Specific pain about "compliance reporting for crypto exchanges" — real but excluded market (X-11). |
| **Kill** | Banal, no buyer, no cost, vendor promo, excluded market, or traceability broken. | Cluster about "developers want better tools" — generic, no specific pain. |

---

## 8. Scoring Calibration Analysis

The scoring calibration analysis examines where the deterministic scoring formula (`pain_cluster_contract.md`, Section 11) diverged from founder judgment, and what adjustments are recommended.

### 8.1 Scoring Component Diagnostic Table

| # | Component | Weight | Observed Problem | Possible Cause | Recommended Adjustment |
|---|-----------|--------|-----------------|----------------|------------------------|
| 1 | `pain_explicitness` | 0.25 | High-scoring clusters had vague or missing actor/workflow | Pain explicitness scoring too generous; evidence with unclear actor was scored 0.5+ instead of <=0.3 | Tighten pain_explicitness criteria: require identifiable actor AND workflow for score >= 0.5 |
| 2 | `pain_explicitness` | 0.25 | Low-scoring clusters had specific, well-described pain that founder valued | Pain explicitness scoring too strict; surface-level extraction missed the pain in verbose evidence | Improve signal extraction to better identify pain in longer-form content |
| 3 | `recurrence` | 0.20 | High recurrence score from comments on a single thread | Recurrence counted comments from the same thread as distinct evidence items without discounting for same-thread clustering | Apply same-thread discount: comments on the same post count as max 2 recurrence points regardless of count |
| 4 | `recurrence` | 0.20 | Cross-source recurrence bonus (1.15x) over-amplified clusters with weak cross-source evidence | Two weak evidence items from different sources boosted above one strong item from a single source | Cap cross-source bonus if individual evidence quality is low |
| 5 | `business_cost` | 0.15 | High business_cost score without cost signal in evidence | Business_cost inferred from domain rather than from explicit cost mention | Require at least one evidence item with explicit cost signal for business_cost >= 0.5 |
| 6 | `business_cost` | 0.15 | Low business_cost score despite clear time/money impact described in evidence | Cost signal present in evidence but not extracted by signal extraction | Improve cost signal detection: explicit time/money/dollar/revenue/loss patterns |
| 7 | `icp_fit` | 0.15 | >80% of clusters scored at default 0.5 — no differentiation | ICP matching not wired into the scoring pipeline; all clusters got the neutral default | Wire ICP matching: compare cluster actor/workflow/domain against ICP profile (Sections 3–5) |
| 8 | `icp_fit` | 0.15 | Founder PROMOTE on cluster with low icp_fit; cluster matched low-priority ICP | ICP fit score was too low because ICP matching missed the alignment | Review ICP matching logic; ensure high-priority ICPs score >= 0.7 when matched |
| 9 | `source_reliability` | 0.10 | Source reliability priors were uniform — no differentiation between sources | Default priors applied; no historical data to differentiate | After Cycle 1, set source reliability priors based on Cycle 1 empirical signal rates |
| 10 | `source_reliability` | 0.10 | Source reliability did not reflect per-repo quality differences for GitHub | Source reliability is per-source, not per-repo; all GitHub repos got the same prior | Consider per-repo reliability sub-scores in Cycle 2 |
| 11 | `freshness` | 0.10 | Stale GitHub issues (2+ years old) scored high freshness because they were "new to the pipeline" | Freshness is based on `fetched_at`, not `created_at`; all items fetched in the same run get similar freshness | Base freshness on original item `created_at`, not `fetched_at` |
| 12 | `freshness` | 0.10 | Freshness was too uniform — did not differentiate recent pains from old issues | All items collected in same run; freshness variation is minimal | If freshness cannot differentiate in a single-run pilot, consider reducing its weight to 0.05 and redistributing to pain_explicitness or business_cost |
| 13 | `actionability` | 0.05 | Actionability was uniformly scored — no differentiation | Actionability scoring too vague; defaulted to 0.5 for all clusters | Define actionability criteria: presence of a suggested validation action, clarity of buyer, feasibility |
| 14 | `noise_risk` | -0.20 | High noise_risk did not suppress enough — noisy clusters still scored >= 0.50 | noise_risk weight (-0.20) was insufficient to counteract other components for genuinely noisy clusters | Increase noise_risk weight to -0.25, or apply a noise gate: if noise_risk >= 0.60, cap overall at 0.49 |
| 15 | `noise_risk` | -0.20 | Low noise_risk on clusters that were clearly noise per founder review | Noise detection missed noise categories (e.g., hype, self-promotion, vague complaints) | Improve noise detection: integrate the noise taxonomy (Section 4) categories into noise_risk scoring |
| 16 | `overall` | — | Many clusters clustered in the 0.40–0.65 range — no clear separation | Scoring components are too flat; not enough differentiation between good and bad clusters | Tune component scoring rubrics to produce more bimodal distribution (good clusters >> 0.70, bad clusters << 0.40) |

### 8.2 Scoring Calibration Procedure

After examining each component, follow this procedure:

1. **Build a founder-alignment matrix:** For each reviewed cluster, plot `overall` score (x-axis) against founder decision (y-axis: PROMOTE / NEEDS_MORE_EVIDENCE / PARK / KILL / REVISIT_LATER).
2. **Identify misalignment quadrants:**
   - **Quadrant I (High score, founder KILL):** Over-promotion. Examine noise_risk, business_cost, icp_fit.
   - **Quadrant II (High score, founder PROMOTE):** Alignment. Scoring is working.
   - **Quadrant III (Low score, founder PROMOTE):** Over-kill. Examine pain_explicitness, business_cost, icp_fit — which components were underweighted?
   - **Quadrant IV (Low score, founder KILL):** Alignment. Scoring is working.
3. **Count misalignments:** Tally clusters in Quadrants I and III vs. total reviewed clusters.
4. **Recommend component adjustments:** Based on the diagnostic table (Section 8.1), recommend specific component adjustments. All adjustments must cite specific pilot evidence (cluster ID, founder decision, rationale).
5. **Do not adjust weights in v2.13.** All adjustments are recommendations for v2.14 implementation.

### 8.3 Example Misalignment Scenarios

| Scenario | Observed | Likely Cause | Recommendation |
|----------|----------|-------------|----------------|
| High score, founder KILL (noise) | Cluster scored 0.72, all evidence is self-promotion | noise_risk was too low; self-promotion not detected | Add self-promotion detection to noise_risk; increase noise_risk weight |
| High score, founder KILL (wrong ICP) | Cluster scored 0.75, pain is about consumer social app | icp_fit was 0.5 (default); cluster should have matched excluded market | Wire ICP matching; ensure excluded markets score icp_fit <= 0.1 |
| Low score, founder PROMOTE | Cluster scored 0.45, founder found it compelling and specific | pain_explicitness or business_cost underweighted; evidence quality was good but not reflected in score | Improve signal extraction for verbose/long-form evidence; review pain_explicitness rubric |
| Medium score, founder PARK | Cluster scored 0.55, founder found it interesting but timing off | Scoring was reasonable; founder PARK is a timing decision, not a quality failure | No scoring adjustment needed; PARK is a valid outcome for medium-score clusters |
| Medium score, founder NEEDS_MORE_EVIDENCE | Cluster scored 0.52, founder found it promising but thin | Recurrence was low; evidence was good but insufficient | No scoring adjustment; recurrence correctly captured thin evidence. Consider lowering promotion threshold for NEEDS_MORE_EVIDENCE flagging |

---

## 9. Query/Repo Tuning Actions

Based on the source-level analysis (Section 6), the following actions may be recommended for Cycle 2. No changes are applied in v2.13. All actions are recommendations for v2.14.

### 9.1 Query/Repo Action Catalog

| Action | Meaning | When to Apply |
|--------|---------|---------------|
| **keep** | Retain the query or repo as-is for Cycle 2. | Signal rate is acceptable; noise rate is acceptable; founder review confirms usefulness. |
| **cap** | Retain but reduce the maximum number of items collected. | Query/repo produces some signal but also high noise; reducing volume may improve signal-to-noise ratio. |
| **revise** | Modify query terms, search logic, or issue filters. | Query terms are too broad or too narrow; issue filters are missing noise categories. |
| **move_to_backup** | Remove from primary collection; keep as optional/additional source for specific investigations. | Query/repo produces occasional useful signal but is mostly noise; not worth regular collection. |
| **kill** | Remove entirely from the Cycle 2 plan. | Query/repo produces unacceptable noise; founder consistently KILLs all evidence from this source; no redeeming signal. |
| **add** | Add a new query bucket or repo to the Cycle 2 plan. | Only if a gap is identified (a useful pain domain not covered by existing queries/repos) AND the founder approves. |
| **add_narrower** | Add a narrower, more specific query or repo to replace a broad one. | Broad query produces too much noise; narrower query might capture the signal more precisely. |
| **add_curated_seed** | Add manually curated seed URLs for specific known-high-signal content. | Some high-signal evidence exists at known URLs but is not captured by generic queries. Requires founder curation. |
| **require_business_cost_terms** | Add query filters requiring business-cost language (time, money, cost, spend, waste, manual). | Query produces too many items without business cost signal. |
| **require_actor_workflow_clarity** | Add post-collection filter requiring identifiable actor AND workflow before signal extraction. | Evidence quality is too low; many items lack clear actor or workflow. |
| **add_noise_flag** | Add a source-specific noise flag (e.g., `hn_show_hn_self_promo`, `github_wishlist`) to detect and filter known noise patterns. | A recurring noise pattern is specific to this source/query/repo and can be detected heuristically. |

### 9.2 Tuning Decision Rules

| Condition | Action |
|-----------|--------|
| Signal rate >= 30% AND founder found at least 1 useful item from this source/query/repo | **keep** |
| Signal rate 15–29% | **cap** or **revise** (depending on noise composition) |
| Signal rate < 15% | **kill** or **move_to_backup** |
| Noise rate > 60% AND noise is dominated by 1–2 identifiable categories | **add_noise_flag** + **revise** |
| Noise rate > 60% AND noise is diverse/unclassifiable | **kill** |
| Single repo dominates >40% of GitHub evidence (even if signal is good) | **cap** (to prevent mono-repo bias) |
| Query produces zero items with `business_cost >= 0.5` | **require_business_cost_terms** or **kill** |
| Query produces >50% items with `pain_explicitness < 0.5` | **require_actor_workflow_clarity** or **kill** |

### 9.3 Example Tuning Recommendations

| Source | Query/Repo | Finding | Recommended Action |
|--------|------------|---------|-------------------|
| HN | Bucket A (AI agent debugging) | 45% signal, 2 founder PROMOTE | **keep** |
| HN | Bucket C (Show HN — devtools) | 12% signal, 70% self-promotion | **kill** or **move_to_backup** |
| HN | Bucket G (broad AI trends) | 8% signal, 60% generic_ai_hype | **kill** |
| GitHub | `langchain-ai/langchain` | 35% signal, useful workflow pain | **keep** |
| GitHub | `crewAIInc/crewAI` | 10% signal, mostly implementation_detail | **move_to_backup** |
| GitHub | `huggingface/transformers` | 5% signal, dominated by one_off_bug and stale_issue | **kill** |

---

## 10. Decision Support for v2.14

This section maps noise and quality analysis findings to the v2.14 roadmap direction. It is the direct input to the item 10 Go / Conditional Go / No-Go Decision.

### 10.1 Mapping to GO

**If the analysis finds:**
- Noise < 40% overall.
- At least 2 strong, specific clusters with founder PROMOTE.
- At least 1–2 PROMOTE candidates with clear validation paths.
- Traceability is clean.
- Founder review was manageable (< 90 minutes) and productive.
- Scoring aligns with founder judgment (>= 80% alignment).
- Cross-source clusters are meaningful.
- Specific sources/queries/repos can be identified as useful.

**Then the recommendation is GO:**
- Run a second pilot cycle to confirm findings.
- Cautiously plan source expansion (Stack Exchange first, then one at a time).
- Keep strong queries/repos from Cycle 1.
- Refine only obvious noise sources (kill the clearly bad queries/repos).
- Do not make major scoring or clustering changes unless clearly justified by data.
- Start planning the v2.14 Source Expansion roadmap.

### 10.2 Mapping to CONDITIONAL GO

**If the analysis finds:**
- Noise 40–80% overall.
- Some useful signal exists but is mixed with significant noise.
- At least 1 cluster/candidate that the founder found worth pursuing.
- Issues are diagnosable — specific sources, queries, repos, or scoring components can be identified as problems.
- Scoring partially aligns with founder judgment (60–79% alignment).
- Founder review was somewhat burdensome but produced insights.
- Traceability is acceptable (minor, fixable issues).

**Then the recommendation is CONDITIONAL GO:**
- v2.14 must be Pilot Quality Improvements, not source expansion.
- Specific fixes scoped by this analysis:
  - **Noise filters:** Implement noise taxonomy categories (Section 4) as heuristic filters.
  - **Query tuning:** Kill/cap/revise queries per Section 9 recommendations.
  - **Repo allowlist tuning:** Remove low-signal repos; cap high-volume repos.
  - **Scoring calibration:** Adjust component rubrics per Section 8 recommendations.
  - **Cluster quality:** Improve near-duplicate detection; add over-merge checks.
  - **Founder review UX:** Improve review package structure based on founder friction notes.
  - **Signal extraction:** Improve pain explicitness detection; tighten actor/workflow/object requirements.
- Re-run pilot after fixes and re-evaluate.
- Do NOT expand sources until quality targets are met.

### 10.3 Mapping to NO-GO

**If the analysis finds:**
- Noise > 80% overall.
- No validatable ideas — nothing passes the "would I test this?" threshold.
- Banal/generic pain clusters.
- Abstract, unactionable opportunity candidates.
- Founder review felt like manual trash sorting.
- Scoring systematically contradicts founder judgment (< 40% alignment).
- Traceability is broken (systematic missing/placeholder URLs).
- Source quality report provides no actionable insights.
- Clustering failures affect >50% of clusters.

**Then the recommendation is NO-GO:**
- Core Discovery Pipeline Repair is required.
- Specific repair areas:
  - **Signal extraction:** Revisit the candidate signal extractor; possibly redesign extraction heuristics.
  - **Scoring:** Revisit the scoring formula weights and component definitions; possibly redesign scoring approach.
  - **PainCluster model:** Revisit cluster identity, deduplication, and cross-source consolidation logic.
  - **Source strategy:** Reconsider whether HN + GitHub Issues are the right sources for the founder's ICP.
  - **ICP alignment:** Revisit whether the ICP profile is specific enough to drive useful filtering.
- Do NOT expand sources until pipeline fundamentals are solid.
- Consider a narrower, more controlled test with manually curated evidence before another operational pilot.

### 10.4 v2.14 Roadmap Hook Summary

| Decision | v2.14 Roadmap | Key Activities |
|----------|---------------|----------------|
| **GO** | Source Expansion Planning | Second pilot cycle; Stack Exchange addition; cautious one-at-a-time source expansion; keep strong queries/repos |
| **CONDITIONAL GO** | Pilot Quality Improvements | Noise filters; query/repo tuning; scoring calibration; cluster quality fixes; founder review UX improvements; re-run pilot |
| **NO-GO** | Core Discovery Pipeline Repair | Revisit signal extraction; revisit scoring; revisit PainCluster model; reconsider source strategy; do not expand sources |

---

## 11. Required Analysis Output

The noise and quality analysis must produce a structured output with the following fields and sections. This output becomes a section within or appendix to the Go/No-Go Decision document (item 10).

### 11.1 Analysis Output Structure

```yaml
analysis_id: "nqa_<run_id>"
run_id: "<discovery_run_id>"
created_at: "<ISO 8601 UTC>"
analyst: "founder" | "system" | "founder+system"

source_quality_findings:
  hacker_news:
    useful: true | false
    overall_signal_rate: <0.0-1.0>
    overall_noise_rate: <0.0-1.0>
    top_useful_buckets: ["<bucket_id>", ...]
    top_noise_buckets: ["<bucket_id>", ...]
    dominant_noise_categories: ["<category>", ...]
    recommendations: ["<action>", ...]
  github_issues:
    useful: true | false
    overall_signal_rate: <0.0-1.0>
    overall_noise_rate: <0.0-1.0>
    top_useful_repos: ["<repo>", ...]
    top_noise_repos: ["<repo>", ...]
    dominant_noise_categories: ["<category>", ...]
    recommendations: ["<action>", ...]
  cross_source:
    useful: true | false
    meaningful_cross_source_clusters: <count>
    source_diversity_useful: true | false

noise_taxonomy_counts:
  generic_ai_hype: <count>
  self_promotion: <count>
  launch_hype: <count>
  flamewar_or_meta_discussion: <count>
  low_text_context: <count>
  one_off_bug: <count>
  implementation_detail_without_business_pain: <count>
  bot_or_maintenance_noise: <count>
  duplicate_or_invalid: <count>
  stale_issue: <count>
  wishlist_without_pain: <count>
  hobby_only: <count>
  unclear_actor: <count>
  unclear_workflow: <count>
  unclear_buyer: <count>
  no_business_cost: <count>
  legal_or_tos_risk: <count>
  source_scope_violation: <count>
  traceability_failure: <count>

query_bucket_findings:
  - bucket_id: "<id>"
    source: "hacker_news"
    signal_rate: <0.0-1.0>
    noise_rate: <0.0-1.0>
    founder_assessment: "useful" | "mixed" | "noise"
    recommended_action: "keep" | "cap" | "revise" | "move_to_backup" | "kill"
    rationale: "<text>"

repo_findings:
  - repo: "<owner/repo>"
    signal_rate: <0.0-1.0>
    noise_rate: <0.0-1.0>
    founder_assessment: "useful" | "mixed" | "noise"
    recommended_action: "keep" | "cap" | "revise" | "move_to_backup" | "kill"
    rationale: "<text>"

cluster_quality_findings:
  - cluster_id: "<id>"
    overall_score: <0.0-1.0>
    founder_decision: "PROMOTE" | "PARK" | "KILL" | "NEEDS_MORE_EVIDENCE" | "REVISIT_LATER"
    specificity: "specific" | "moderate" | "generic"
    source_diversity: <1-3>
    cross_source_meaningful: true | false | n/a
    scoring_aligned: true | false
    recommended_cluster_action: "promote" | "split" | "merge" | "park" | "kill"
    recommended_action_rationale: "<text>"

scoring_calibration_findings:
  alignment_rate: <0.0-1.0>
  over_promotions: <count>
  over_kills: <count>
  flat_distribution: true | false
  component_issues:
    - component: "<name>"
      problem: "<description>"
      recommendation: "<text>"
  recommended_weight_changes: ["<text>", ...]

founder_review_burden:
  total_time_minutes: <int>
  exceeded_target: true | false
  exceeded_maximum: true | false
  system_recommendation_overrides: <count>
  review_package_clarity: "clear" | "adequate" | "confusing"
  evidence_links_useful: true | false
  source_quality_report_useful: true | false
  friction_points: ["<text>", ...]

top_quality_problems:
  - problem: "<description>"
    severity: "critical" | "high" | "medium" | "low"
    affected_dimension: "<dimension from Section 3>"
    evidence: "<citation from pilot data>"

recommended_fixes:
  - fix: "<description>"
    target_roadmap: "v2.14"
    category: "noise_filter" | "query_tuning" | "repo_tuning" | "scoring_calibration" | "cluster_quality" | "founder_review_ux" | "signal_extraction" | "traceability"
    priority: "must_fix" | "should_fix" | "nice_to_fix"

recommended_next_roadmap: "GO" | "CONDITIONAL GO" | "NO-GO"
recommended_next_roadmap_rationale: "<text summarizing the evidence for this recommendation>"

open_questions:
  - "<question that cannot be answered with Cycle 1 data alone>"
```

### 11.2 Analysis Output Rules

- The analysis output must cite specific evidence from pilot artifacts (cluster IDs, evidence IDs, source URLs, metrics).
- Every recommended fix must be traceable to a specific observation in the analysis dimensions (Section 3).
- The `recommended_next_roadmap` must be consistent with the quality thresholds (Section 5) and the decision support mapping (Section 10).
- `open_questions` must only contain questions that genuinely cannot be answered with Cycle 1 data — not questions that were simply not investigated.

---

## 12. Do-Not-Do Rules

During noise and quality analysis, the following constraints apply:

| # | Rule | Rationale |
|---|------|-----------|
| 1 | **Do not excuse bad results by saying "need more sources" too early.** | Source expansion is the most expensive and least targeted fix. Diagnose the existing pipeline first. More sources do not fix broken scoring or clustering. |
| 2 | **Do not expand sources before diagnosing core pipeline.** | Adding sources to a broken pipeline produces more noise, not more signal. The NO-GO path exists for this reason. |
| 3 | **Do not change scoring based on one anecdote without founder review evidence.** | Scoring calibration must be based on patterns across multiple founder decisions, not a single cluster. |
| 4 | **Do not delete noisy evidence without recording reason.** | Every evidence item excluded as noise must have a recorded noise category (Section 4). Silent deletions destroy audit trail. |
| 5 | **Do not ignore traceability failures.** | A broken `source_url` invalidates the evidence item. Traceability failures are critical severity. Do not proceed to Go decision with unresolved traceability issues. |
| 6 | **Do not treat GitHub/HN as representative of all markets.** | HN and GitHub Issues are developer-heavy sources. They do not represent SMB owners, finance teams, operations managers, or other non-developer ICPs. Acknowledge this bias. |
| 7 | **Do not promote ideas with no buyer.** | "Interesting technology" without a reachable buyer is not an opportunity. Do not count it toward the "ideas worth validating" threshold. |
| 8 | **Do not lower the bar for "validatable idea" to make the pilot look successful.** | If nothing passes the "would I test this?" threshold, record that honestly. A NO-GO decision based on honest data is more valuable than a GO based on lowered standards. |
| 9 | **Do not treat neutral `icp_fit` (0.5) as alignment.** | The default 0.5 means "no information," not "moderate fit." Clusters with default icp_fit have not been ICP-matched. |
| 10 | **Do not apply v2.14 fixes in v2.13.** | All tuning recommendations are scoped for v2.14. v2.13 does not modify scoring, clustering, queries, repos, or extraction logic. |

---

## 13. Definition of Done

Item 9 is done when:

- [ ] **13.1** Noise and quality analysis framework document exists at `docs/decisions/noise_quality_analysis_framework_v2_13.md`.
- [ ] **13.2** Noise taxonomy exists with >= 15 categories, each with meaning, examples, likely source, and recommended response (Section 4).
- [ ] **13.3** Quality thresholds are defined: Excellent, Acceptable, Problematic, Failing (Section 5).
- [ ] **13.4** Source-level analysis questions exist for HN (>= 10 questions) and GitHub Issues (>= 10 questions) (Section 6).
- [ ] **13.5** Cluster-level analysis questions exist (>= 7 per-cluster questions) with cluster action catalog (Section 7).
- [ ] **13.6** Scoring calibration framework exists with component diagnostic table (>= 10 rows) and calibration procedure (Section 8).
- [ ] **13.7** Query/repo tuning actions are defined with decision rules and example recommendations (Section 9).
- [ ] **13.8** v2.14 decision support mapping exists: GO, CONDITIONAL GO, NO-GO paths with specific activities (Section 10).
- [ ] **13.9** Analysis output structure is defined with all required fields (Section 11).
- [ ] **13.10** Do-not-do rules are defined (>= 10 rules) (Section 12).
- [ ] **13.11** Roadmap item 9 marked complete in `docs/roadmaps/OOS_roadmap_v2_13_operational_pilot_go_no_go_checklist.md`.
- [ ] **13.12** `.\scripts\dev-git-check.ps1` passes.
- [ ] **13.13** `git status --short` shows only allowed files before commit.
- [ ] **13.14** One local commit made with message: `[v2.13] 9 define noise quality analysis`.

---

*Noise and Quality Analysis Framework v2.13. Operational analysis procedure only. Does not modify source code, tests, scripts, scoring, clustering, or portfolio state. All tuning recommendations are scoped for v2.14.*
