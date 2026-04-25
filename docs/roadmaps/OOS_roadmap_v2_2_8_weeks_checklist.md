# OOS Roadmap v2.2 — 8 Weeks Checklist

## 0. Current Position

- [x] **0.1.1** Roadmap v1 completed: **8 / 8 mini-epics**
- [x] **0.1.2** OOS has a working Windows-native weekly cycle
- [x] **0.1.3** Real signal batch ingestion exists
- [x] **0.1.4** Founder review package exists
- [x] **0.1.5** `weekly-cycle-status` exists
- [x] **0.1.6** AI-assisted ideation exists behind a feature flag
- [x] **0.1.7** AI ideation evaluation and rollback rules exist
- [ ] **0.2.1** Current phase: **Roadmap v2.2 — AI Meaning Layer**
- [ ] **0.2.2** Current item: **7.1**
- [ ] **0.2.3** Total mini-epics in this roadmap: **16**
- [ ] **0.2.4** Completed from this roadmap: **12 / 16**
- [ ] **0.2.5** Remaining: **4 / 16**

---

## 1. Core Principle

```text
LLM = meaning, analysis, formulation, critique
Heuristics = baseline / fallback / control group
Code = structure, validation, traceability, reproducibility
Human = final decision
```

The goal is not to make deterministic heuristics pretend to be intelligent. The goal is to make OOS process real signals through a controlled AI meaning loop:

```text
real signals
→ pre-clustering dedup
→ LLM signal understanding
→ LLM semantic clustering
→ LLM opportunity framing
→ pattern-guided LLM ideation
→ deterministic anti-pattern checks
→ isolated AI council critique
→ founder review
→ founder decision
→ weekly summary
```

---

## 2. Global Rules for Every Mini-Epic

Every mini-epic must include validation immediately. Validation is not postponed to the end.

### Required in every mini-epic

- [ ] Schema / contract validation
- [ ] Traceability validation
- [ ] Stage-level fallback behavior if AI output fails
- [ ] Focused tests
- [ ] Windows-native validation commands
- [ ] Roadmap update only after validation passes
- [ ] Commit + push after acceptance

### AI artifact metadata required everywhere

Every LLM-produced artifact must include:

```text
prompt_name
prompt_version
model_id
input_hash
generation_mode
created_at
linked_input_ids
fallback_used
stage_confidence
stage_status
```

### Prompt versioning rule

Prompt changes must create a new prompt version.

Examples:

```text
signal_extractor_v1
signal_extractor_v2
opportunity_framer_v1
ideation_constrained_v1
council_skeptic_v1
```

Silent prompt edits are not allowed because they make old and new outputs incomparable.

### Stage-level rollback rule

Every AI stage must define its own fallback / rollback condition.

Examples:

```text
Signal extraction:
if fewer than 80% of signals receive valid structured meaning → degraded extraction mode

Signal quality scoring:
if fewer than 80% of scores are valid → preserve raw signal routing and mark scoring_unavailable

Clustering:
if all clusters have confidence < 0.4 → fallback to simple grouping and mark low_confidence_clustering

Opportunity framing:
if opportunity has no linked evidence → park/reject and mark evidence_missing

Ideation:
if fewer than 2 distinct product patterns are produced → low_diversity warning and fallback candidate generation

Council:
if no role finds a serious risk → suspiciously_clean = true
```

Fallbacks must be visible in artifacts. They must not pretend to be full analysis.

---

## 3. Operational Constraints

### LLM call budget

The previous 6–12 call estimate is too low for a naive per-signal architecture. Roadmap v2.2 assumes batching where possible.

### Batching strategy

Signal extraction and quality scoring should be batched by chunks instead of one call per signal.

Initial batching targets:

```text
Small batch size: 10–20 signals
Extraction/scoring chunk size: 5–10 signals per call
```

### Expected LLM calls per batch

For a batch of 10–20 signals:

```text
Economy mode:
8–12 calls
- batched extraction + scoring: 2–4
- clustering: 1
- opportunity framing: 1–2
- ideation: 1–2
- lightweight critique / summary: 2–3

Standard mode:
14–25 calls
- batched extraction + scoring: 3–6
- clustering: 1
- opportunity framing: 2–3
- ideation: 2–4
- isolated council calls: 5–10

Deep mode:
30+ calls
- multiple opportunity cards
- multiple top ideas
- five isolated council roles per top idea
- deeper evaluation / comparison
```

### Warning thresholds

```text
Economy mode warning: >12 calls
Standard mode warning: >25 calls
Deep mode warning: >40 calls
```

### Latency budget

```text
Single LLM call timeout: configurable
Default timeout: 60 seconds
Batch soft timeout: configurable
```

### Caching strategy

At minimum, cache by:

```text
input_hash + prompt_version + model_id
```

### Failure policy

```text
System-level LLM stage failure rate > 25% → degraded mode / fallback recommendation
```

Stage-level thresholds are defined inside each mini-epic.

---

## 4. FounderReviewPackage v2 — Target Artifact Shape

```text
artifacts/founder_review/
  inbox.md
  index.json
  sections/
    signals.md
    dedup.md
    clusters.md
    opportunities.md
    ideas.md
    anti_patterns.md
    critiques.md
    decisions.md
    ai_quality.md
```

### `index.json` should include

```json
{
  "package_id": "...",
  "run_id": "...",
  "created_at": "...",
  "review_items": [],
  "linked_signal_ids": [],
  "latest_weekly_review": "...",
  "decision_commands": []
}
```

Each roadmap phase may add content to the founder package, but it must do so through this structure.

---

# Phase 1 — Foundation for Measurable AI Work

## 1.1. Evaluation dataset v0 + heuristic baseline reframe
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done  
**Week:** 1

### Goal

Create a small repeatable evaluation dataset immediately and clearly define heuristic ideation as baseline / fallback / control group.

### Dataset v0 target

- minimum 15 signals
- at least 4 required edge cases
- 2 expected semantic clusters
- 2 expected opportunity directions
- 4–6 expected idea-quality notes
- explicit quality notes from founder / operator

### Dataset scope note

Dataset v0 is a smoke-test and early calibration fixture only. Real quality calibration begins with the expanded v1 dataset after several real batches.

### Dataset realism rule

Real signals are preferred. Synthetic signals are allowed only if real signals are unavailable.

Synthetic signals must be explicitly labeled:

```json
{
  "synthetic": true
}
```

Dataset v0 must include at least 4 edge cases:

- 2 intentionally ambiguous cases
- 1 duplicate or near-duplicate case
- 1 weak/noisy signal
- 1 signal with unclear buyer or unclear pain

### Heuristic baseline role

Current heuristic ideation should be documented as:

```text
good placeholder
good fallback
good control group
not good primary ideation engine
```

### Tasks

- [x] **1.1.1** Create `examples/evaluation_dataset_v0/`
- [x] **1.1.2** Add at least 15 real signals, or synthetic signals clearly labeled as synthetic
- [x] **1.1.3** Add at least 4 required edge cases, including 2 intentionally ambiguous cases
- [x] **1.1.4** Add at least 1 duplicate or near-duplicate case
- [x] **1.1.5** Add expected cluster notes
- [x] **1.1.6** Add expected opportunity notes
- [x] **1.1.7** Add founder/operator quality notes
- [x] **1.1.8** Document heuristic ideation as baseline / fallback / control
- [x] **1.1.9** Add artifact metadata for ideation mode:
  - [x] **1.1.9.1** `heuristic_baseline`
  - [x] **1.1.9.2** `llm_assisted`
  - [x] **1.1.9.3** `heuristic_fallback_after_llm_failure`
- [x] **1.1.10** Add focused tests for dataset loading and mode labeling

### Definition of Done

- [x] Evaluation dataset v0 exists with at least 15 signals
- [x] Real vs synthetic status is explicit
- [x] Dataset includes at least 4 required edge cases
- [x] Dataset includes duplicate / near-duplicate case
- [x] Dataset can be loaded by tests
- [x] Heuristic ideation is documented as baseline/fallback/control
- [x] Idea artifacts clearly show generation mode
- [x] Tests are green
- [x] Roadmap updated only after validation

---

## 1.2. AI contracts, prompt versioning, and operational constraints
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done  
**Week:** 1

### Goal

Create shared infrastructure rules for AI outputs before building multiple AI layers.

### Tasks

- [x] **1.2.1** Define common AI artifact metadata fields
- [x] **1.2.2** Add prompt version tracking
- [x] **1.2.3** Add model ID tracking
- [x] **1.2.4** Add input hash tracking
- [x] **1.2.5** Add LLM call budget tracking
- [x] **1.2.6** Add timeout / failure metadata
- [x] **1.2.7** Add cache key convention:
  - [x] **1.2.7.1** `input_hash`
  - [x] **1.2.7.2** `prompt_version`
  - [x] **1.2.7.3** `model_id`
- [x] **1.2.8** Add batching strategy documentation
- [x] **1.2.9** Add economy/standard/deep mode budget documentation
- [x] **1.2.10** Add stage-level rollback policy convention
- [x] **1.2.11** Document operational constraints in README / docs
- [x] **1.2.12** Add focused tests for metadata and prompt versioning

### Definition of Done

- [x] Every new LLM artifact type can carry prompt/model/input metadata
- [x] Prompt versioning convention is documented
- [x] Call budget and failure policy are documented
- [x] Batching strategy is documented
- [x] Cache key convention is documented
- [x] Stage-level rollback convention is documented
- [x] Tests are green
- [x] Roadmap updated only after validation

---

# Phase 2 — Pre-Processing and AI Signal Understanding

## 2.1. Pre-clustering dedup / fingerprinting
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done  
**Week:** 2

### Goal

Prevent duplicate or near-duplicate signals from inflating clusters and recurrence signals.

### Dedup types

- exact duplicate hash
- normalized text fingerprint
- near-duplicate similarity marker
- duplicate group ID
- canonical signal ID

### Near-duplicate algorithm

The near-duplicate method must be fixed before implementation, not chosen during implementation.

Default algorithm:

```text
near_duplicate = cosine similarity >= 0.85
on normalized signal text
```

If another method is chosen, it must be explicitly documented before implementation and covered by tests.

### Tasks

- [x] **2.1.1** Add normalized signal fingerprinting
- [x] **2.1.2** Add exact duplicate detection
- [x] **2.1.3** Add near-duplicate candidate detection using the documented threshold / method
- [x] **2.1.4** Add duplicate group metadata:
  - [x] **2.1.4.1** `duplicate_group_id`
  - [x] **2.1.4.2** `is_duplicate`
  - [x] **2.1.4.3** `canonical_signal_id`
- [x] **2.1.5** Ensure duplicates are not physically deleted
- [x] **2.1.6** Ensure clustering can use canonicalized signal set
- [x] **2.1.7** Add focused tests for exact and near duplicates

### Definition of Done

- [x] Duplicates are detected before clustering
- [x] Near-duplicate threshold / method is documented before implementation
- [x] Duplicate metadata is stored
- [x] No signal is deleted automatically
- [x] Clustering can avoid inflated recurrence from duplicates
- [x] Tests are green
- [x] Roadmap updated only after validation

---

## 2.2. LLM signal meaning extraction + quality scoring
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done  
**Week:** 2

### Goal

Use batched LLM calls to extract structured meaning and quality signals from real inputs.

### AI should extract

- actor / user segment
- pain
- context
- current workaround
- urgency
- cost signal
- evidence
- uncertainty
- confidence

### Signal quality scoring fields

- specificity
- recurrence potential
- workaround
- cost signal
- urgency
- confidence
- explanation

### Stage-level rollback

```text
If fewer than 80% of non-duplicate signals receive valid structured extraction:
→ degraded extraction mode
→ preserve raw signal
→ mark analysis_unavailable for failed signals
```

### Tasks

- [x] **2.2.1** Add batched LLM signal extraction adapter behind a feature flag
- [x] **2.2.2** Define strict output schema for extracted signal meaning
- [x] **2.2.3** Add signal quality scoring to the same stage or adjacent batched stage
- [x] **2.2.4** Store extracted meaning as artifacts linked to original `signal_id`
- [x] **2.2.5** Validate extracted schema immediately
- [x] **2.2.6** Add fallback behavior for invalid/missing LLM output
- [x] **2.2.7** Include required AI metadata:
  - [x] **2.2.7.1** prompt version
  - [x] **2.2.7.2** model ID
  - [x] **2.2.7.3** input hash
  - [x] **2.2.7.4** generation mode
- [x] **2.2.8** Preserve existing weak/noise routing behavior
- [x] **2.2.9** Ensure founder can still promote weak signals manually
- [x] **2.2.10** Add focused tests for:
  - [x] **2.2.10.1** valid LLM extraction
  - [x] **2.2.10.2** invalid LLM extraction
  - [x] **2.2.10.3** fallback preserving raw signal
  - [x] **2.2.10.4** traceability to `signal_id`
  - [x] **2.2.10.5** quality scoring

### Definition of Done

- [x] Each processed non-duplicate signal has structured meaning when LLM extraction succeeds
- [x] Raw signal is preserved when LLM extraction fails
- [x] Signal quality score exists when scoring succeeds
- [x] Artifact includes AI metadata and analysis mode
- [x] Traceability to original `signal_id` is preserved
- [x] Existing routing behavior remains compatible
- [x] Tests are green
- [x] Roadmap updated only after validation

---

# Phase 3 — AI Semantic Clustering and Contradictions

## 3.1. LLM semantic clustering of canonical signals
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done  
**Week:** 3

### Goal

Group canonical, deduplicated signals by meaning, not by repeated words.

### Cluster fields

- `cluster_id`
- title
- summary
- linked `signal_ids`
- linked canonical signal IDs
- reasoning
- confidence
- uncertainty

### Stage-level rollback

```text
If all clusters have confidence < 0.4:
→ fallback to simple grouping
→ mark low_confidence_clustering = true
```

### Tasks

- [x] **3.1.1** Add LLM semantic clustering adapter
- [x] **3.1.2** Use canonicalized signal set from 2.1
- [x] **3.1.3** Define cluster output schema
- [x] **3.1.4** Validate all linked `signal_ids`
- [x] **3.1.5** Prevent empty or orphan clusters
- [x] **3.1.6** Include prompt/model/input metadata
- [x] **3.1.7** Add focused tests for:
  - [x] **3.1.7.1** valid clustering
  - [x] **3.1.7.2** missing signal references
  - [x] **3.1.7.3** invalid cluster output
  - [x] **3.1.7.4** fallback behavior
  - [x] **3.1.7.5** duplicate inflation avoidance

### Definition of Done

- [x] Signals can be grouped by semantic meaning
- [x] Duplicates do not inflate cluster recurrence
- [x] Each cluster explains why signals belong together
- [x] Code validates references and schema
- [x] Traceability is preserved
- [x] Tests are green
- [x] Roadmap updated only after validation

---

## 3.2. Contradiction detection and merge candidates
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done  
**Week:** 3

### Goal

Detect contradictions, duplicates, near-duplicates, and merge candidates before opportunity framing.

### Working definition of contradiction

Two signals are contradictory if they describe the same situation or process but give mutually exclusive assessments of:

- pain
- workaround
- urgency
- buyer/user need
- trust in current solution

### Example

Signal A:

```text
Owner does not trust reports because Excel and bank balances diverge.
```

Signal B:

```text
Owner fully trusts current reporting; the only problem is report preparation speed.
```

These may describe the same reporting context but contradict each other about the pain.

### Tasks

- [x] **3.2.1** Add contradiction report
- [x] **3.2.2** Add merge candidates list
- [x] **3.2.3** Preserve all original signals; do not auto-delete
- [x] **3.2.4** Include traceability for every dedup / contradiction claim
- [x] **3.2.5** Mark contradiction severity:
  - [x] **3.2.5.1** low
  - [x] **3.2.5.2** medium
  - [x] **3.2.5.3** high
- [x] **3.2.6** Add focused tests

### Definition of Done

- [x] Contradictions are surfaced with clear definition
- [x] Merge candidates are visible
- [x] No signal is deleted automatically
- [x] Traceability is preserved
- [x] Tests are green
- [x] Roadmap updated only after validation

---

# Phase 4 — AI Opportunity Framing

## 4.1. LLM opportunity cards with defined non-obvious angle
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done  
**Week:** 4

### Goal

Turn semantic clusters into useful opportunity cards.

### Opportunity card fields

- title
- target user
- pain
- current workaround
- why it matters
- evidence
- urgency
- possible wedge
- monetization hypothesis
- risks
- assumptions
- non-obvious angle
- linked `cluster_id`
- linked `signal_ids`

### Definition of `non_obvious_angle`

`non_obvious_angle` is a thesis that either:

1. contradicts the first obvious interpretation of the problem, or
2. identifies a segment, wedge, or monetization mechanism that does not follow directly from the literal signal wording.

Bad example:

```text
SMB owners need better financial dashboards.
```

Better example:

```text
The wedge may not be reporting itself, but restoring owner trust in financial data through weekly reconciliation narratives.
```

### Stage-level rollback

```text
If opportunity has no linked evidence:
→ park/reject opportunity
→ mark evidence_missing = true
```

### Tasks

- [x] **4.1.1** Add LLM opportunity framing adapter
- [x] **4.1.2** Define opportunity card schema
- [x] **4.1.3** Require evidence for claims
- [x] **4.1.4** Mark unsupported claims as assumptions
- [x] **4.1.5** Add `non_obvious_angle` with the strict definition above
- [x] **4.1.6** Include prompt/model/input metadata
- [x] **4.1.7** Add tests for:
  - [x] **4.1.7.1** valid opportunity card
  - [x] **4.1.7.2** missing evidence
  - [x] **4.1.7.3** unsupported assumptions
  - [x] **4.1.7.4** non-obvious angle
  - [x] **4.1.7.5** traceability

### Definition of Done

- [x] Opportunity cards are generated from clusters
- [x] Claims are linked to evidence or marked as assumptions
- [x] `non_obvious_angle` is meaningful under the strict definition
- [x] Founder review can show evidence and uncertainty
- [x] Tests are green
- [x] Roadmap updated only after validation

---

## 4.2. Opportunity quality gate
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done  
**Week:** 4

### Goal

Prevent weak or pretty-but-empty opportunities from moving forward.

### Gate criteria

- clear user
- concrete pain
- evidence
- urgency or cost
- possible product angle
- risks / uncertainty
- traceability

### Tasks

- [x] **4.2.1** Add opportunity quality gate
- [x] **4.2.2** Add statuses:
  - [x] **4.2.2.1** pass
  - [x] **4.2.2.2** park
  - [x] **4.2.2.3** reject
- [x] **4.2.3** Add AI explanation for recommendation
- [x] **4.2.4** Keep founder override capability
- [x] **4.2.5** Validate required fields immediately
- [x] **4.2.6** Add tests for pass/park/reject cases

### Definition of Done

- [x] Each opportunity receives a gate recommendation
- [x] Recommendation has an explanation
- [x] Code validates required fields
- [x] Founder can override
- [x] Tests are green
- [x] Roadmap updated only after validation

---

# Phase 5 — LLM Primary Ideation

## 5.1. Pattern-guided LLM ideation
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done  
**Week:** 5

### Goal

Make LLM the main source of meaningful idea generation while using product patterns to avoid repetitive generic SaaS output.

### Required idea fields

- idea title
- target user
- pain addressed
- product concept
- wedge
- why now
- business model options
- first experiment
- key assumptions
- risks
- selected product pattern
- linked opportunity ID
- linked signal IDs
- generation mode

### Required diversity

The LLM must generate idea variants across different product shapes, for example:

- SaaS / tool
- service-assisted workflow
- data product
- marketplace / brokered workflow
- internal automation product
- audit / risk radar
- expert-in-the-loop workflow

### Stage-level rollback

```text
If fewer than 2 distinct product patterns are produced:
→ add low_diversity warning
→ use fallback candidate generation if needed
```

### Tasks

- [x] **5.1.1** Add product pattern library
- [x] **5.1.2** Expose pattern options to LLM ideation prompt/provider boundary
- [x] **5.1.3** Require 3–5 idea variants per opportunity
- [x] **5.1.4** Require different product shapes
- [x] **5.1.5** Add pattern metadata to idea artifacts
- [x] **5.1.6** Keep heuristic fallback, clearly labeled as fallback
- [x] **5.1.7** Include prompt/model/input metadata
- [x] **5.1.8** Add tests for:
  - [x] **5.1.8.1** successful LLM idea generation
  - [x] **5.1.8.2** invalid LLM output fallback
  - [x] **5.1.8.3** idea diversity
  - [x] **5.1.8.4** pattern diversity
  - [x] **5.1.8.5** traceability

### Definition of Done

- [x] LLM produces multiple genuinely different idea variants
- [x] Each idea includes business model and first experiment
- [x] Ideas use different product patterns
- [x] Heuristic fallback is labeled and not confused with primary ideation
- [x] Downstream pipeline remains compatible
- [x] Tests are green
- [x] Roadmap updated only after validation

---

## 5.2. Ideation mode comparison with weighted metrics
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done  
**Week:** 5

### Goal

Compare ideation modes honestly using operationalized and weighted metrics.

### Modes to compare

- current heuristic baseline
- improved heuristic / pattern-library baseline
- LLM-constrained ideator

### Metrics table

| Criterion | Scored by | Scale | Weight / Role |
|---|---:|---:|---|
| Schema validity | code | pass/fail | Required gate |
| Traceability | code | pass/fail | Required gate |
| Relevance to input pain | LLM + optional founder | 1–3 | ×2 |
| Novelty / diversity | LLM + pattern check | 1–3 | ×1 |
| Commercial usefulness | founder | 1–3 | ×2 |
| Founder fit | founder | 1–3 | ×2 |
| Testability | LLM + code checks | 1–3 | ×1 |
| Automation potential | LLM | 1–3 | ×1 |
| Hallucination risk | LLM + code evidence check | 1–3 | subtract ×1 |
| Genericness penalty | code + LLM | 0 / -1 / -2 | penalty |

### Suggested aggregate score

```text
total_score =
2 * relevance_to_pain
+ novelty
+ 2 * commercial_usefulness
+ 2 * founder_fit
+ testability
+ automation_potential
- hallucination_risk
+ genericness_penalty
```

Schema validity and traceability are gates, not optional score components.

### Preliminary thresholds

These thresholds are preliminary and must be recalibrated after the first real batches:

```text
score >= 12 → candidate for council review
score 8–11 → park / low priority
score < 8 → auto-park
```

The final council-selection threshold should be fixed here after real-batch calibration.

### Tasks

- [x] **5.2.1** Extend evaluation report to compare all ideation modes
- [x] **5.2.2** Implement metric ownership and scales
- [x] **5.2.3** Implement weighted aggregate score
- [x] **5.2.4** Add genericness penalty
- [x] **5.2.5** Add diversity score
- [x] **5.2.6** Add commercial usefulness and founder fit scores
- [x] **5.2.7** Add rollback / use recommendation
- [x] **5.2.8** Add preliminary score thresholds
- [x] **5.2.9** Add focused tests

### Definition of Done

- [x] Evaluation report compares modes clearly
- [x] Metrics have scorer, scale, and aggregation
- [x] Commercial usefulness, founder fit, and relevance have higher weights
- [x] Preliminary thresholds are documented and used
- [x] Heuristic mode is treated as baseline/control
- [x] LLM mode is judged by usefulness, not text prettiness
- [x] Report includes recommendation
- [x] Tests are green
- [x] Roadmap updated only after validation

---

# Phase 6 — Anti-Patterns and AI Council

## 6.1. Deterministic anti-pattern checks
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done  
**Week:** 6

### Goal

Add cheap deterministic checks for common weak idea patterns before expensive AI council critique.

### This layer is deterministic

It should use rules / keywords / simple structural checks. It should not replace LLM critique.

### Anti-patterns

- generic dashboard
- generic chatbot
- generic AI assistant
- “Uber for X”
- pure consulting disguised as product
- founder-time-heavy service
- unclear buyer
- no urgent pain
- no clear first experiment

### Tasks

- [x] **6.1.1** Add deterministic anti-pattern library
- [x] **6.1.2** Add anti-pattern check to idea evaluation
- [x] **6.1.3** Add genericness warning to founder review
- [x] **6.1.4** Add penalty to ranking/evaluation
- [x] **6.1.5** Keep this layer cheap and non-LLM
- [x] **6.1.6** Add tests for common anti-patterns

### Definition of Done

- [x] Ideas are checked against deterministic anti-patterns
- [x] Generic ideas receive warnings and penalties
- [x] Founder sees anti-pattern warnings
- [x] LLM calls are not used for this layer
- [x] Tests are green
- [x] Roadmap updated only after validation

---

## 6.2. Isolated AI council critique with suspiciously_clean protection
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done  
**Week:** 6

### Goal

Add semantic/contextual critique roles that evaluate idea quality and AI reasoning quality.

### Definition of top ideas

Council critique applies only to selected top ideas, not to every generated idea.

Initial selection rule:

```text
top ideas = ideas with total_score >= council_threshold
OR top N by score if fewer ideas cross the threshold
```

Preliminary threshold is inherited from section 5.2:

```text
score >= 12 → candidate for council review
```

In standard mode:

```text
maximum 3 ideas per opportunity go to council critique
```

Exact thresholds must be recalibrated in 5.2 after the first real batches.

### Difference from 6.1

- **6.1** = cheap deterministic filters
- **6.2** = expensive semantic LLM critique for ideas that pass initial checks

### Minimum roles

- Skeptic
- Market Reality Checker
- Founder Bottleneck Checker
- Commercialization Critic
- Genericness Detector

### Call architecture

Each role must run as an isolated LLM call with its own prompt.

Do not run all roles in one combined prompt.

After all isolated role calls complete, aggregate them into a Critique Summary.

### Role instruction

The Skeptic must search for ways the idea can die, not merely balance pros and cons.

### Critique checks

- Does the idea really follow from signals?
- Is it too generic in this specific context?
- Is there a clear buyer?
- Can it be tested quickly?
- Does it turn into consulting?
- What is the weakest assumption?
- Where might the AI have hallucinated?

### Suspiciously clean rule

If no critique role finds a serious risk or kill candidate, set:

```text
suspiciously_clean = true
```

This requires founder manual review.

### Stage-level rollback

```text
If council role outputs are missing or invalid:
→ preserve idea
→ mark critique_unavailable
→ require founder manual review
```

### Tasks

- [x] **6.2.1** Add top-idea selection rule for council critique
- [x] **6.2.2** Add isolated AI critique role outputs
- [x] **6.2.3** Add structured critique schema
- [x] **6.2.4** Add Critique Summary aggregator after isolated calls
- [x] **6.2.5** Link critique to idea IDs and signal IDs
- [x] **6.2.6** Include hallucination / unsupported-claim checks
- [x] **6.2.7** Add `suspiciously_clean` flag
- [x] **6.2.8** Add recommendation schema:
  - [x] **6.2.8.1** kill
  - [x] **6.2.8.2** park
  - [x] **6.2.8.3** test now
  - [x] **6.2.8.4** needs more evidence
- [x] **6.2.9** Require explanation and next action
- [x] **6.2.10** Preserve founder decision as final authority
- [x] **6.2.11** Add tests for critique generation, validation, isolated calls, top-idea selection, and suspiciously clean cases

### Definition of Done

- [x] Council only runs on selected top ideas
- [x] Standard mode sends at most 3 ideas per opportunity to council
- [x] Each council role is an isolated LLM call
- [x] Each top idea receives structured critique
- [x] Critique identifies weaknesses and first test
- [x] Unsupported AI claims are flagged
- [x] Suspiciously clean cases are flagged
- [x] Founder decision overrides AI recommendation
- [x] Weekly review shows both AI recommendation and founder decision
- [x] Tests are green
- [x] Roadmap updated only after validation

---

# Phase 7 — Founder Review and Quality Feedback

## 7.1. FounderReviewPackage v2 implementation
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [ ] Done  
**Week:** 7

### Goal

Implement the target founder review package structure so the founder can review the AI meaning loop without artifact hunting.

### Target structure

```text
artifacts/founder_review/
  inbox.md
  index.json
  sections/
    signals.md
    dedup.md
    clusters.md
    opportunities.md
    ideas.md
    anti_patterns.md
    critiques.md
    decisions.md
    ai_quality.md
```

### Tasks

- [ ] **7.1.1** Implement package structure
- [ ] **7.1.2** Add signals section
- [ ] **7.1.3** Add dedup section
- [ ] **7.1.4** Add clusters section
- [ ] **7.1.5** Add opportunities section
- [ ] **7.1.6** Add ideas section
- [ ] **7.1.7** Add anti-patterns section
- [ ] **7.1.8** Add critiques section
- [ ] **7.1.9** Add decisions section
- [ ] **7.1.10** Add AI quality section
- [ ] **7.1.11** Preserve `review_id` decision workflow
- [ ] **7.1.12** Add focused tests

### Definition of Done

- [ ] Founder review package has fixed structure
- [ ] Package can be read without artifact hunting
- [ ] Every section links back to source artifacts
- [ ] `review_id` workflow still works
- [ ] Tests are green
- [ ] Roadmap updated only after validation

---

## 7.2. Founder rating by AI stage + evaluation dataset v1 expansion
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [ ] Done  
**Week:** 7

### Goal

Let founder rate AI output quality by stage and expand the evaluation dataset.

### Ratings

- good
- okay
- weak
- wrong

### Stages

- signal understanding
- clustering
- opportunity framing
- ideation
- critique

### Dataset v1 target

- 20–30 real signals
- 5–8 semantic clusters
- 5 opportunity cards
- 15–25 idea variants
- founder quality notes

Synthetic cases remain allowed only when explicitly labeled.

### Tasks

- [ ] **7.2.1** Add rating artifact model
- [ ] **7.2.2** Add CLI command to record AI-stage rating
- [ ] **7.2.3** Show ratings in weekly summary
- [ ] **7.2.4** Preserve links to related artifacts
- [ ] **7.2.5** Expand evaluation dataset from v0 to v1
- [ ] **7.2.6** Add expected-quality notes
- [ ] **7.2.7** Add repeatable evaluation command
- [ ] **7.2.8** Add focused tests

### Definition of Done

- [ ] Founder can rate AI output by stage
- [ ] Ratings are saved
- [ ] Weekly summary shows AI quality signals
- [ ] Dataset v1 exists
- [ ] Synthetic cases are explicitly labeled
- [ ] Evaluation can be repeated
- [ ] Results can be compared across prompt/model versions
- [ ] Tests are green
- [ ] Roadmap updated only after validation

---

# Phase 8 — Final E2E Verification and Completion

## 8.1. Full AI meaning loop verification
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [ ] Done  
**Week:** 8

### Goal

Verify the full AI-powered meaning loop end-to-end.

### Final scenario

```text
real signals
→ pre-clustering dedup
→ LLM signal understanding
→ LLM semantic clustering
→ contradiction report
→ LLM opportunity framing
→ opportunity quality gate
→ pattern-guided LLM ideation
→ ideation mode comparison
→ deterministic anti-pattern checks
→ isolated AI council critique
→ founder review package
→ founder decision
→ AI quality rating
→ weekly summary
```

### Tasks

- [ ] **8.1.1** Add final end-to-end AI meaning loop test
- [ ] **8.1.2** Run full loop on evaluation dataset v1
- [ ] **8.1.3** Verify traceability from weekly summary back to source signals
- [ ] **8.1.4** Verify duplicates do not inflate clusters
- [ ] **8.1.5** Verify founder decision recording
- [ ] **8.1.6** Verify AI quality ratings appear in weekly summary
- [ ] **8.1.7** Verify LLM metadata appears in AI artifacts
- [ ] **8.1.8** Verify prompt versions are logged
- [ ] **8.1.9** Verify LLM call count is reported
- [ ] **8.1.10** Run full Windows-native verification

### Definition of Done

- [ ] Full loop passes on evaluation dataset v1
- [ ] Traceability is preserved
- [ ] Duplicate inflation is prevented
- [ ] Founder decision is recorded
- [ ] Weekly summary includes AI quality signals
- [ ] LLM metadata is present
- [ ] LLM call count is visible
- [ ] `verify.ps1` is green
- [ ] Roadmap updated only after validation

---

## 8.2. Roadmap v2.2 completion checkpoint
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [ ] Done  
**Week:** 8

### Goal

Close Roadmap v2.2 cleanly after final verification.

### Checkpoint artifact ownership

The final checkpoint must have two parts:

1. **Founder-written narrative**
   - capabilities
   - learnings
   - decisions
   - judgment of usefulness

2. **System-generated report**
   - actual LLM call counts
   - latency profile
   - quality scores from evaluation dataset
   - fallback / failure summary

Both artifacts must exist for this mini-epic to be complete.

### Tasks

- [ ] **8.2.1** Add final Roadmap v2.2 checkpoint document
- [ ] **8.2.2** Add founder-written narrative section / artifact
- [ ] **8.2.3** Add system-generated report section / artifact
- [ ] **8.2.4** Summarize what AI meaning loop can and cannot do
- [ ] **8.2.5** Summarize cost / latency profile from actual runs
- [ ] **8.2.6** Summarize quality findings from evaluation dataset
- [ ] **8.2.7** Tag release:
  - [ ] **8.2.7.1** `roadmap-v2.2-complete`
- [ ] **8.2.8** Mark roadmap complete:
  - [ ] **8.2.8.1** Completed: `16 / 16`
  - [ ] **8.2.8.2** Remaining: `0 / 16`
  - [ ] **8.2.8.3** Current item: `Completed / final milestone state`

### Definition of Done

- [ ] Checkpoint document exists
- [ ] Founder-written narrative exists
- [ ] System-generated report exists
- [ ] Cost / latency profile is documented
- [ ] Quality findings are documented
- [ ] Release tag exists
- [ ] Roadmap v2.2 is complete
- [ ] Main branch contains final merged work

---

## 9. Milestones

- [x] **9.1** Milestone A: Measurement foundation ready after **1.2**
- [x] **9.2** Milestone B: AI signal understanding operational after **2.2**
- [x] **9.3** Milestone C: AI semantic clustering operational after **3.2**
- [x] **9.4** Milestone D: AI opportunity framing operational after **4.2**
- [x] **9.5** Milestone E: LLM primary ideation and comparison operational after **5.2**
- [x] **9.6** Milestone F: Anti-pattern and AI council critique operational after **6.2**
- [ ] **9.7** Milestone G: Founder review and AI quality feedback operational after **7.2**
- [ ] **9.8** Milestone H: Roadmap v2.2 complete after **8.2**

---

## 10. Tracking Rules

- [ ] **10.1** Always record current status as: `Current item: X.Y`
- [ ] **10.2** Always record progress as: `Completed: N / 16`
- [ ] **10.3** Always record remaining work as: `Remaining: M / 16`
- [ ] **10.4** Mark mini-epics only when Definition of Done is actually met
- [ ] **10.5** Update this roadmap only after validation passes
- [ ] **10.6** After each accepted mini-epic: commit + push
- [ ] **10.7** Merge accepted work into `main` before starting the next mini-epic, unless explicitly decided otherwise
- [ ] **10.8** Do not defer schema validation to the end of the roadmap
- [ ] **10.9** Do not introduce new LLM prompts without prompt versioning
- [ ] **10.10** Do not treat fluent AI output as good output without evaluation
- [ ] **10.11** Do not exceed LLM call budget silently
- [ ] **10.12** Do not run council roles in one combined prompt

---

## 11. Execution Rules

- [ ] **11.1** Follow phase order unless explicitly changed
- [ ] **11.2** Any reordering must be written into the roadmap
- [ ] **11.3** Every mini-epic must include exact validation commands
- [ ] **11.4** Every mini-epic must preserve traceability
- [ ] **11.5** Every AI mini-epic must include prompt/version metadata
- [ ] **11.6** Every AI mini-epic must define fallback behavior
- [ ] **11.7** Every accepted mini-epic must be merged or clearly tracked before moving on
- [ ] **11.8** Every LLM-heavy mini-epic must report expected and actual call count

---

## 12. Explicit Non-Goals for Roadmap v2.2

- [ ] **12.1** No UI
- [ ] **12.2** No database migration
- [ ] **12.3** No multi-user workflow
- [ ] **12.4** No scheduler / daemon
- [ ] **12.5** No live external connectors
- [ ] **12.6** No training of own model
- [ ] **12.7** No automatic decisions without founder
- [ ] **12.8** No attempt to make heuristic ideation the main “smart” engine
- [ ] **12.9** No architecture refactor for aesthetics only
- [ ] **12.10** No unbounded LLM-call expansion without budget/caching
- [ ] **12.11** No Windows temp cleanup work inside the AI roadmap unless required by a current mini-epic

---

## 13. Maintenance Backlog — Outside Roadmap v2.2

These items are real but not part of the AI Meaning Layer roadmap.

- [ ] **13.1** Windows temp cleanup hygiene
- [ ] **13.2** `.test-tmp` ACL issue
- [ ] **13.3** `git status` warnings caused by locked temp folders
- [ ] **13.4** Ensure `verify.ps1` leaves no avoidable garbage
- [ ] **13.5** Review local Codex sandbox / approval ergonomics

---

## 14. Notes

- Use `[x]` for done
- Use `[-]` manually in text if you want to mark something as in progress inside comments or headings
- Keep this file updated after each accepted mini-epic
- Do not mark AI output as “good” merely because it is fluent
- Evaluation must reward usefulness, traceability, diversity, testability, and commercial realism
- Penalize generic dashboards, generic assistants, and consulting-heavy “products”
- Council must be adversarial enough to find failure modes
- If no serious critique appears, mark result as `suspiciously_clean`
- Synthetic evaluation signals must be labeled
- Duplicate signals must not inflate recurrence or cluster strength
- Near-duplicate detection threshold must be fixed before implementation
- Council critique should be expensive, isolated, and limited to selected top ideas
- Final checkpoint must include both founder-written and system-generated artifacts
