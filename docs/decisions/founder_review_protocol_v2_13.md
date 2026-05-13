# OOS v2.13 — Founder Review Protocol

**Title:** OOS v2.13 — Founder Review Protocol
**Status:** Draft / operational review protocol
**Roadmap item:** v2.13 item 7
**Branch:** `ops/v2-13-operational-pilot-cycle-1`
**Created:** 2026-05-13
**Based on:**
- [Founder ICP Preference Profile v2.13](founder_icp_preference_profile_v2_13.md)
- [Pilot Cycle 1 Brief v2.13](pilot_cycle_1_brief_v2_13.md)
- [Pilot Run Procedure v2.13](pilot_run_procedure_v2_13.md)
- [Operational Discovery Pilot Run Contract](../contracts/operational_discovery_pilot_run_contract.md)
- [PainCluster Contract](../contracts/pain_cluster_contract.md)

---

## 1. Purpose

The purpose of this protocol is to turn Pilot Cycle 1 outputs into structured founder judgments:

- which pains are interesting;
- which candidates are specific and business-relevant;
- which are banal/noise;
- which deserve validation;
- whether OOS is useful enough to continue.

This is **not**:
- automated decision-making;
- portfolio mutation;
- `KillReason` record creation;
- source expansion approval;
- production validation;
- code, test, script, or artifact modification.

This **is**:
- a structured review protocol defining how the founder inspects pilot outputs;
- how the founder scores, records decisions, and distinguishes useful opportunities from noise;
- how the founder prepares the Go / Conditional Go / No-Go decision.

This protocol does **not** create actual founder decision artifacts. It defines the review process and required founder notes only. Any future founder decision artifact creation belongs only to a later explicitly approved workflow.

---

## 2. Inputs to Review

The founder review package must include the following artifacts. All artifacts are pre-verified by the Pilot Run Procedure (Section 8, checks V-1 through V-21) before handoff.

### 2.1 Mandatory Review Inputs

| # | Artifact | Format | Description |
|---|----------|--------|-------------|
| 1 | `founder_review_package.md` | Markdown | Primary review document: ranked clusters, opportunity candidates, evidence links, advisory recommendations |
| 2 | `founder_review_package.json` | JSON | Structured version of the review package |
| 3 | `source_quality_report.md` | Markdown | Human-readable quality summary: which sources/queries worked, which produced noise |
| 4 | `source_quality_report.json` | JSON | Machine-readable quality metrics |
| 5 | `validation_summary.json` | JSON | Confirmation that all validation checks passed; `is_valid` must be `true` |
| 6 | `pilot_run_manifest.json` | JSON | Run metadata: parameters, counts, approvals, limitations |

### 2.2 Optional Deeper-Inspection Inputs

| # | Artifact | Format | Description |
|---|----------|--------|-------------|
| 7 | `pain_clusters.json` | JSON | Full cluster data if deeper inspection of a specific cluster is needed |
| 8 | `candidate_signals.json` | JSON | Full candidate signal list if deeper inspection of evidence is needed |
| 9 | `raw_evidence.json` | JSON | Original raw evidence if traceability or source quality of a specific item must be verified |

### 2.3 Reference Documents

The founder should have these documents available during review:

| # | Document | Purpose |
|---|----------|---------|
| R1 | [Founder ICP Preference Profile v2.13](founder_icp_preference_profile_v2_13.md) | ICP definitions, excluded markets, relevance signals, noise definitions, review rubric |
| R2 | [Pilot Cycle 1 Brief v2.13](pilot_cycle_1_brief_v2_13.md) | Success/failure criteria, timebox, decision outcomes |
| R3 | This protocol | Review order, decision definitions, scoring rubric, note requirements |

---

## 3. Review Timebox

### 3.1 Timing Rules

| # | Rule | Detail |
|---|------|--------|
| T1 | **Start window** | Review should begin within 48 hours after pilot run handoff |
| T2 | **Target review time** | 60–120 minutes of active review time |
| T3 | **Review burden signal** | If review takes more than 2 hours, this is evidence of a review package / pipeline quality problem |
| T4 | **Maximum review time** | Do not exceed 3 hours; if not done by then, record what was completed and document why the package was not reviewable within the target window |

### 3.2 Recommended Session Split

| Phase | Duration | Activity |
|-------|----------|----------|
| **Phase 1: Source quality scan** | 15 minutes | Review Source Quality Report; understand noise/signal breakdown; note which sources/queries performed |
| **Phase 2: Candidate review** | 45–75 minutes | Review top pain clusters and opportunity candidates; assign decisions and notes |
| **Phase 3: Go/No-Go notes** | 15–30 minutes | Summarize findings; prepare inputs for the Go/No-Go decision |

### 3.3 Time Management Rules

- Review items in ranked order (highest score first).
- Spend more time on high-scoring, interesting items; less time on obvious noise.
- If an item is clearly banal/noise, decide quickly (KILL) and move on.
- If an item resists quick classification, mark it `NEEDS_MORE_EVIDENCE` or `REVISIT_LATER` and move on.
- Do not let one item consume disproportionate review time.

---

## 4. Review Order

The founder must follow this step-by-step review order. Skipping steps or reviewing out of order may produce inconsistent judgments.

### Step-by-Step Review Order

| Step | Action | Input | Output |
|------|--------|-------|--------|
| **1** | Confirm `validation_summary` is valid | `validation_summary.json` | Confirmed: `is_valid` is `true`; all checks passed |
| **2** | Confirm source URL traceability is clean | `validation_summary.json`, traceability section | Confirmed: zero missing URLs, zero placeholder URLs |
| **3** | Review Source Quality Report | `source_quality_report.md`, `source_quality_report.json` | Understanding of noise/signal per source; which queries/repos to tune |
| **4** | Review top PainClusters | `founder_review_package.md`, `founder_review_package.json` | Per-cluster review: inspect pain pattern, evidence, scores |
| **5** | Review top opportunity candidates | `founder_review_package.md`, `founder_review_package.json` | Per-candidate review: inspect problem statement, evidence, suggested actions |
| **6** | Assign founder decision to each review item | This protocol, Sections 6–7 | One decision per item: PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER |
| **7** | Mark interesting / banal / unclear / actionable | This protocol, Section 8 | One quality marker per item |
| **8** | Assign suggested validation action | This protocol, Section 9 | One validation action per item (or `kill_no_action` for KILL) |
| **9** | Record review burden/friction | This protocol, Section 13 | Review burden assessment notes |
| **10** | Prepare inputs for Go/No-Go decision | This protocol, Section 15 | Summary counts, top opportunities, source quality assessment, alignment notes |

### Review Order Enforcement

- Steps 1–2 are **gates**: if `validation_summary.is_valid` is not `true`, or traceability is broken, do **not** proceed to review. Escalate to the pilot run procedure failure handling (Section 11).
- Steps 3–10 are the review body. They must be completed in order.
- Step 10 feeds directly into the Go/No-Go decision (roadmap item 10).

---

## 5. Review Item Fields to Inspect

For each review item presented in the founder review package, inspect the following fields. If a field is missing or uninformative, note it as a quality flag.

### 5.1 Required Inspection Fields

| # | Field | Description | What to Check |
|---|-------|-------------|---------------|
| 1 | `review_item_id` | Unique identifier for this review item | Present, non-empty |
| 2 | `pain_cluster_id` | The source PainCluster ID | Present; format `pc_<16char_hex>` |
| 3 | `opportunity_id` | The source Opportunity Candidate ID (if framed) | Present if an opportunity candidate was framed; format `oppc_<8char_hex>` |
| 4 | `title` | Short title describing the pain or opportunity | Specific, not generic; contains actor/workflow/object |
| 5 | `actor` | Who experiences the pain | Specific role/persona; not "people" or "developers in general" |
| 6 | `workflow` | The task or workflow being disrupted | Specific process; not a vague domain |
| 7 | `object` | The tool, system, or process causing the pain | Concrete noun phrase |
| 8 | `pain_pattern` | Normalized pain statement | Readable single sentence; contains actor + workflow + object + pain verb |
| 9 | `score` | Overall cluster score (0.0–1.0) | Present; computed from the deterministic scoring formula |
| 10 | `score_components` | Full breakdown: pain_explicitness, recurrence, business_cost, icp_fit, source_reliability, freshness, actionability, noise_risk | All 8 components present; each in 0.0–1.0 |
| 11 | `source_diversity` | Count of distinct source types | >= 1; >= 2 is stronger |
| 12 | `recurrence` | Number of distinct evidence items | >= 1 |
| 13 | `business_relevance` | 0.0–1.0 assessment | Present; not defaulted to 0.5 unless genuinely neutral |
| 14 | `noise_risk` | 0.0–1.0 assessment | Present; should be low for high-score items |
| 15 | `evidence_links` | List of source URLs supporting this item | At least one real `http(s)://` URL per item |
| 16 | `source_ids` | Source identifiers for evidence | `hacker_news` and/or `github_issues` |
| 17 | `recommendation_reason` | Why the system recommends a particular decision | Present; logically connected to the evidence |
| 18 | `suggested_validation_action` | System-suggested next step | One of: `interview`, `landing_page`, `manual_research`, `collect_more_evidence`, `kill_no_action` |
| 19 | `source_quality_notes` | Notes from the Source Quality Report about this item's sources | Present; helps interpret evidence quality |
| 20 | `traceability_status` | Must be `clean` for every item | `clean`, not `broken` or `partial` |

### 5.2 Missing or Poor Fields

If a review item has missing fields, generic values, or poor-quality decomposition:

- Note it as a quality flag (see Section 14).
- This may indicate a pipeline quality problem.
- Do not skip the item; review it with the information available and mark the deficiency.

---

## 6. Founder Decisions

The founder must assign exactly one of five decisions to every reviewed item. Decisions must be recorded in structured form, not free-text.

### 6.1 Decision Definitions

#### PROMOTE

**Definition:** The opportunity or pain cluster is worth real validation now.

**Criteria — ALL of the following should hold:**
- Specific pain with clear actor and workflow.
- Clear ICP/buyer from the high or medium priority ICP list (ICP-1 through ICP-10).
- Evidence from more than one source OR repeated evidence from one source.
- Business cost visible (time, money, risk).
- Plausible validation path in 1–2 weeks.
- Legally clean.
- Founder is interested enough to spend time on it.

**Effect:** This item is a candidate for real-world validation (interview, landing page, manual research). It will be listed as a top opportunity in the Go/No-Go decision input.

#### NEEDS_MORE_EVIDENCE

**Definition:** The pain or opportunity is promising but evidence is thin.

**Criteria — ANY of the following:**
- Interesting pain but evidence from a single source only.
- Low recurrence (1–2 evidence items).
- ICP/buyer unclear but pain looks real.
- Missing willingness-to-pay signal.
- Missing buyer clarity.
- Scoring is moderate but uncertainty is high.

**Effect:** This item is preserved for further investigation. It should be revisited after more data cycles or after additional manual research. It does not block a Go decision but indicates the pipeline needs more input.

#### PARK

**Definition:** The item is moderately interesting but not urgent or not aligned with current focus.

**Criteria — ANY of the following:**
- Moderately interesting but not urgent.
- Unclear monetization path.
- Not aligned with current founder focus or Pilot Cycle 1 focus themes (F-1 through F-7).
- Timing unclear but worth remembering.
- Would be interesting in a different market cycle.

**Effect:** This item is set aside. It may be revisited in a future cycle if conditions change. It does not count toward the "ideas worth validating" threshold.

#### KILL

**Definition:** The item is not worth pursuing now or ever.

**Criteria — ANY of the following:**
- Banal / generic pain (matches noise patterns N-1 through N-9 from the ICP profile).
- No identifiable buyer.
- No feasible validation path in 1–2 weeks.
- Legally or ethically problematic.
- Excluded market (matches X-1 through X-12 from the ICP profile).
- Vendor promo / launch disguised as pain.
- High noise, no real signal.
- Too far from preferred domains with no redeeming signal.

**KILL requires a written founder rationale explaining why the idea died, not just labeling it.** The rationale must answer: "What specifically makes this not worth pursuing?"

Good rationale: `"All three evidence items are self-promotion from the same author; no genuine user pain."`
Bad rationale: `"Noise."`

Good rationale: `"Pain is about personal home-lab dashboards; no business cost, no buyer."`
Bad rationale: `"Not interesting."`

Acceptable rationale categories include: `too_generic`, `no_buyer`, `vendor_promo_false_positive`, `no_real_pain`, `not_aligned`, `excluded_market`, `no_validation_path`, `founder_bottleneck`, `ethical_conflict`, `single_source_no_recurrence`, `too_abstract`, `hobby_only`, `technical_curiosity_only`.

**This protocol does not create `KillReason` records or kill archive entries.** Any future `KillReason` artifact creation belongs only to a later explicitly approved workflow.

#### REVISIT_LATER

**Definition:** The item is possibly interesting but timing, market readiness, or evidence scope is insufficient now.

**Criteria — ANY of the following:**
- Possibly interesting but timing unclear.
- Market not ready (technology, regulation, adoption).
- Requires source expansion beyond current scope (HN + GitHub Issues).
- Depends on external trend that hasn't matured.
- Would benefit from more data cycles (e.g., 2–3 more weekly runs).

**Effect:** This item is noted for future cycles. It should be explicitly listed in the Go/No-Go decision input as a "revisit later" candidate.

### 6.2 Decision Summary Table

| Decision | Meaning | When to Use | Validation Action |
|----------|---------|-------------|-------------------|
| **PROMOTE** | Worth real validation now | Specific pain, clear ICP, business cost, plausible validation, founder interest | `interview`, `landing_page`, or `manual_research` |
| **NEEDS_MORE_EVIDENCE** | Promising but evidence thin | Single-source, low recurrence, unclear ICP/buyer | `collect_more_evidence`, `search_more_sources`, `inspect_github_repos` |
| **PARK** | Interesting but not now | Moderate interest, unclear monetization, timing off | None required now; revisit in future cycle |
| **KILL** | Not worth pursuing | Banal, no buyer, excluded market, vendor promo, no validation path | `kill_no_action` |
| **REVISIT_LATER** | Check again after more cycles | Timing unclear, market immature, needs source expansion | None required now; revisit trigger set |

### 6.3 Decision Recording Format

Each decision must be recorded with:

```
review_item_id: <id>
decision: PROMOTE | PARK | KILL | NEEDS_MORE_EVIDENCE | REVISIT_LATER
rationale: <one-sentence explanation of why>
marker: interesting | banal | unclear | actionable
suggested_validation_action: <action or kill_no_action>
founder_comment: <optional free-text>
system_recommendation_match: match | partial_match | mismatch
mismatch_reason: <if mismatch, explain why>
```

---

## 7. Required Founder Notes Per Item

For every reviewed item, the founder must provide the following notes. No item may be left without a decision and rationale.

### 7.1 Required Note Fields

| # | Field | Required | Description |
|---|-------|----------|-------------|
| 1 | `decision` | **Yes** | One of: `PROMOTE`, `PARK`, `KILL`, `NEEDS_MORE_EVIDENCE`, `REVISIT_LATER` |
| 2 | `rationale` | **Yes** | One-sentence explanation of why this decision was made. Must reference specific evidence or criteria. |
| 3 | `marker` | **Yes** | Exactly one of: `interesting`, `banal`, `unclear`, `actionable` |
| 4 | `suggested_validation_action` | **Yes** (unless KILL) | One of the allowed validation actions (see Section 9). Use `kill_no_action` for KILL decisions. |
| 5 | `founder_comment` | **No** | Optional free-text comment for additional context, questions, or observations. |
| 6 | `system_recommendation_match` | **Yes** | Whether the system recommendation matched the founder's final decision: `match`, `partial_match`, or `mismatch`. |
| 7 | `mismatch_reason` | **Conditional** | Required if `system_recommendation_match` is `partial_match` or `mismatch`. Explain why the founder disagreed with the system. |

### 7.2 Marker Definitions

| Marker | Meaning | When to Use |
|--------|---------|-------------|
| `interesting` | Worth the founder's attention; real pain or promising pattern | Pain is specific, buyer is clear, evidence is plausible |
| `banal` | Generic, obvious, or low-signal; no unique insight | Matches noise patterns N-1 through N-9; "everyone knows this" |
| `unclear` | Ambiguous; needs more data to classify | Pain is plausible but evidence is thin, buyer unclear, or pattern hard to judge |
| `actionable` | Specific enough to act on; validation path is clear | Pain is concrete, buyer is reachable, next step is obvious |

### 7.3 Rationale Writing Rules

- Must be one sentence (may be a compound sentence if needed).
- Must reference specific evidence from the review item (actor, workflow, pain pattern, source, or score component).
- Must not be generic ("interesting", "not relevant").
- For KILL: must explain why the idea died, not just label it.
- For PROMOTE: must state what makes this worth validating now.

**Examples:**

- PROMOTE: `"Specific pain about AI agent debugging with clear developer ICP, 2-source evidence, and a reachable validation path via interviews."`
- KILL: `"Generic 'build a dashboard for X' suggestion with no specific actor, no business cost, and single-source low-detail evidence."`
- NEEDS_MORE_EVIDENCE: `"Data pipeline validation pain looks real but only one GitHub issue supports it; need more repos or HN evidence to confirm."`
- PARK: `"Interesting integration pain between tools, but not aligned with current focus themes; revisit if focus expands to integration tools."`
- REVISIT_LATER: `"AI agent cost tracking pain; market is early, tools are immature, but pattern may strengthen in 3–6 months."`

---

## 8. Validation Actions

For every item not receiving a KILL decision, the founder must assign a suggested validation action. For KILL decisions, use `kill_no_action`.

### 8.1 Allowed Validation Actions

| Action | When to Use | Description |
|--------|-------------|-------------|
| `interview` | Pain is specific, buyer is clear, and the founder can reach potential users | Talk to 3–5 potential users to validate the pain, understand workarounds, and gauge willingness to pay |
| `landing_page` | Pain is clear, ICP is reachable online, and demand can be tested with minimal build | Create a simple landing page describing the solution; measure sign-up interest |
| `manual_research` | Pain is plausible but needs deeper investigation before interviews | Research existing solutions, competitors, market size, pricing benchmarks |
| `collect_more_evidence` | Pain is promising but evidence is thin | Expand query scope, add search terms, or broaden repo allowlist for this specific pain domain |
| `check_competitors` | Pain domain has known players; need to understand the competitive landscape | Identify existing solutions, their pricing, their gaps, and user complaints about them |
| `inspect_github_repos` | Pain is technical/devtools; more GitHub evidence may exist | Search additional GitHub repos for similar issues; check issue comments for workaround descriptions |
| `search_more_sources` | Pain may appear in sources not yet in scope | If Go decision, plan to check Stack Exchange, Reddit, or other sources for this specific pain |
| `kill_no_action` | Item is KILLED | No further action; rationale recorded |

### 8.2 Validation Action Assignment Rules

| Decision | Default Validation Action | Alternatives |
|----------|--------------------------|--------------|
| PROMOTE | `interview` | `landing_page`, `manual_research` |
| NEEDS_MORE_EVIDENCE | `collect_more_evidence` | `inspect_github_repos`, `search_more_sources`, `manual_research` |
| PARK | (none required) | May optionally note a future action |
| KILL | `kill_no_action` | — |
| REVISIT_LATER | (none required) | May optionally note what would trigger revisit |

### 8.3 Validation Action Detail

For PROMOTE items with `interview` or `landing_page`, the founder should briefly note:

- **Interview:** Who to talk to (ICP segment, how to find them, 2–3 interview questions).
- **Landing page:** What value proposition to test, where to drive traffic, what to measure.
- **Manual research:** What specifically to investigate (competitors, market, pricing, tech feasibility).

These notes are optional but recommended for items the founder intends to act on.

---

## 9. Founder Judgment Scoring

To support consistent review, the founder should score each item against a simple 0–2 rubric across 10 dimensions. This scoring guides review; it does **not** replace the founder's decision.

### 9.1 Scoring Rubric

| # | Dimension | 0 | 1 | 2 |
|---|-----------|---|---|---|
| D1 | **Pain specificity** | Vague/generic; no actor, workflow, or object | Partially specific; some dimensions clear | Fully specific; actor, workflow, object, pain verb all clear |
| D2 | **Buyer/ICP clarity** | No identifiable buyer | Buyer segment is plausible but not specific | Clear, named ICP segment; founder can find these buyers |
| D3 | **Workflow clarity** | No workflow described | Workflow is mentioned but steps unclear | Workflow is clear: inputs, steps, outputs described |
| D4 | **Recurrence** | Single evidence item only | 2–3 evidence items | 4+ evidence items, preferably cross-source |
| D5 | **Business cost** | No cost implied | Cost implied but not quantified | Cost quantified or clearly described (time, money, risk) |
| D6 | **Reachable validation path** | No feasible validation path in <1 month | Validation path exists but requires significant prep | Clear validation path achievable in 1–2 weeks |
| D7 | **Willingness-to-pay plausibility** | No WTP signal; no reason to believe anyone would pay | Indirect WTP signal (tool spend, workaround cost) | Direct WTP signal (stated willingness, existing paid alternatives) |
| D8 | **Founder interest** | Founder is not interested or domain is outside expertise/interest | Moderate interest; domain is adjacent to founder expertise | High interest; domain is core founder expertise and passion |
| D9 | **Legal/ethical cleanliness** | Legally or ethically problematic; ToS-hostile | Minor legal/ethical concerns; manageable | Clean; no legal or ethical concerns |
| D10 | **Differentiation / non-banalness** | Generic/banal; "everyone knows this" or "obvious AI wrapper" | Somewhat differentiated; specific angle | Clearly differentiated; non-obvious insight or underserved niche |

### 9.2 Score Interpretation

| Total Score | Interpretation | Typical Decision |
|-------------|---------------|-----------------|
| **16–20** | Strong candidate; specific, clear ICP, business cost, validation path | PROMOTE |
| **11–15** | Promising but gaps; evidence, ICP, or validation path needs work | NEEDS_MORE_EVIDENCE or PARK |
| **6–10** | Weak; too generic, unclear buyer, low evidence | Likely KILL |
| **0–5** | Noise; banal, no buyer, no cost, no validation path | KILL |

### 9.3 Scoring Rules

- Score each dimension independently; do not let overall impression drive individual dimension scores.
- Score based on evidence in the review item, not on assumptions about the market.
- If a dimension cannot be scored from the available evidence, score it 0 and note the missing information.
- The total score is **advisory only**. The founder's final decision may differ from what the score suggests. Document any divergence in `system_recommendation_match` and `mismatch_reason`.

### 9.4 Scoring Worksheet

Use this worksheet for each reviewed item:

```
Review Item: <review_item_id>
Title: <title>

| Dimension | Score (0/1/2) |
|-----------|---------------|
| D1: Pain specificity        |   |
| D2: Buyer/ICP clarity       |   |
| D3: Workflow clarity        |   |
| D4: Recurrence              |   |
| D5: Business cost           |   |
| D6: Reachable validation path |   |
| D7: WTP plausibility        |   |
| D8: Founder interest        |   |
| D9: Legal/ethical cleanliness |   |
| D10: Differentiation        |   |
| **TOTAL**                   |   |

Founder decision: ___________
Score interpretation matches decision? Yes / No
If No, why: _________________________________
```

---

## 10. System Alignment Check

For every reviewed item, record whether the system's recommended decision matched the founder's final decision. This supports later analysis of scoring quality, cluster quality, and pipeline calibration.

### 10.1 Alignment Categories

| Alignment | Definition | Example |
|-----------|------------|---------|
| `match` | Founder decision is exactly the same as the system recommendation | System: `review_for_promotion` → Founder: `PROMOTE` |
| `partial_match` | Founder decision is adjacent but not identical | System: `review_for_promotion` → Founder: `NEEDS_MORE_EVIDENCE` |
| `mismatch` | Founder decision is contradictory to the system recommendation | System: `review_for_promotion` → Founder: `KILL` |

### 10.2 Alignment Recording

For each reviewed item, record:

```
review_item_id: <id>
system_recommendation: <system's advisory recommendation>
founder_decision: <founder's final decision>
alignment: match | partial_match | mismatch
mismatch_reason: <if not match, explain why>
```

### 10.3 Alignment Summary

After all items are reviewed, compute the alignment summary:

| Metric | Count |
|--------|-------|
| Total items reviewed | N |
| `match` count | N |
| `partial_match` count | N |
| `mismatch` count | N |
| Match rate | (matches / total) × 100% |

### 10.4 Alignment Analysis

Alignment patterns that indicate pipeline quality issues:

- **Systematic over-promotion:** System recommends PROMOTE on items the founder KILLs → `icp_fit` or `business_relevance` scoring may be too generous; noise filters may be too permissive.
- **Systematic over-killing:** System recommends KILL on items the founder PROMOTEs → scoring is too conservative; `noise_risk` penalty may be too aggressive.
- **Random mismatch:** No clear pattern; scoring may be poorly calibrated overall.
- **High match rate (>70%):** Scoring is reasonably well-aligned with founder judgment.

Record alignment observations in the review burden assessment (Section 13) and the Go/No-Go inputs (Section 15).

---

## 11. Review Output Format

The founder review notes should be recorded in a structured format. This can be Markdown, JSON, or both. The recommended structure follows.

### 11.1 Review Session Header

```markdown
# Founder Review Notes — Pilot Cycle 1
**Review Session ID:** `founder_review_session_YYYY-MM-DD_<8char_hex>`
**Reviewer:** <founder name>
**Reviewed at:** <ISO 8601 UTC timestamp>
**Run ID:** <pilot run ID from pilot_run_manifest.json>
**Review duration:** <actual time spent>
**Protocol version:** founder_review_protocol_v2_13
```

### 11.2 Review Summary Section

```markdown
## Review Summary

| Metric | Count |
|--------|-------|
| Total items reviewed | N |
| PROMOTE | N |
| PARK | N |
| KILL | N |
| NEEDS_MORE_EVIDENCE | N |
| REVISIT_LATER | N |
```

### 11.3 Per-Item Decision Records

```markdown
## Per-Item Decisions

### <review_item_id> — <title>

- **Decision:** PROMOTE | PARK | KILL | NEEDS_MORE_EVIDENCE | REVISIT_LATER
- **Rationale:** <one-sentence explanation>
- **Marker:** interesting | banal | unclear | actionable
- **Suggested validation action:** <action>
- **Founder judgment score:** <total>/20 (D1:N, D2:N, D3:N, D4:N, D5:N, D6:N, D7:N, D8:N, D9:N, D10:N)
- **System recommendation:** <system's advisory recommendation>
- **Alignment:** match | partial_match | mismatch
- **Mismatch reason:** <if applicable>
- **Founder comment:** <optional>
```

### 11.4 System Alignment Summary Section

```markdown
## System Alignment Summary

| Metric | Count |
|--------|-------|
| Match | N |
| Partial match | N |
| Mismatch | N |
| Match rate | N% |

**Alignment notes:** <observations about alignment patterns>
```

### 11.5 Top Opportunities Section

```markdown
## Top Opportunities

The following items were PROMOTEd and are candidates for real-world validation:

1. **<review_item_id> — <title>**
   - Score: <overall>
   - Source diversity: N
   - Recurrence: N
   - Suggested validation action: <action>
   - Rationale: <founder rationale>
```

### 11.6 Killed as Noise Summary

```markdown
## Killed as Noise Summary

The following items were KILLED:

| review_item_id | Title | Kill Rationale | Noise Pattern |
|---------------|-------|----------------|---------------|
| <id> | <title> | <rationale> | <N-1 through N-9 or other> |
```

### 11.7 Follow-Up Actions

```markdown
## Follow-Up Actions

- [ ] <action 1>
- [ ] <action 2>
- ...
```

### 11.8 Artifact Policy for Review Notes

- Founder review notes are **runtime artifacts**.
- They must be written to the same `output_dir` as other pilot outputs.
- They must **not** be committed to the repository unless explicitly approved (AG-5).
- The review notes file should be named: `founder_review_notes_v2_13.md` (and optionally `founder_review_notes_v2_13.json`).
- This protocol defines the expected structure; it does not create the notes file.

---

## 12. Review Burden Assessment

After completing the review, the founder should answer the following questions. These answers inform the Go/No-Go decision and pipeline quality assessment.

### 12.1 Burden Assessment Questions

| # | Question | Answer Format |
|---|----------|---------------|
| B1 | Was the review manageable within 2 hours? | Yes / No. If No, how long did it take? |
| B2 | Were review items understandable? | Yes / Partially / No. If not, what was unclear? |
| B3 | Were evidence links useful? | Yes / Partially / No. Could you verify evidence origin? |
| B4 | Were PainClusters specific or abstract? | Mostly specific / Mixed / Mostly abstract. Examples? |
| B5 | Did the scoring help or distract? | Helped / Neutral / Distracted. Why? |
| B6 | Did the Source Quality Report help? | Yes / Partially / No. What was useful or missing? |
| B7 | Was there too much manual trash sorting? | Yes / Some / No. Approximately what % of items were obviously noise? |
| B8 | What should be improved before Cycle 2? | Free text: specific, scoped recommendations. |

### 12.2 Burden Thresholds

| Signal | Threshold | Interpretation |
|--------|-----------|----------------|
| Review took >2 hours | Review package quality problem | Too many items, poorly organized, or excessive noise |
| >50% of items were obvious noise | Pipeline noise filter insufficient | `noise_risk` scoring not aggressive enough; query plans need tuning |
| Evidence links not useful | Traceability may be formal but not functional | URLs exist but don't help founder verify evidence |
| Scoring distracted more than helped | Scoring calibration problem | Scores don't match founder intuition; weights may need tuning |
| PainClusters mostly abstract | Clustering quality problem | Pain decomposition fields are generic; pipeline not extracting specifics |

### 12.3 Burden Assessment Recording

Record the burden assessment in the review notes under a dedicated section:

```markdown
## Review Burden Assessment

- **Review manageable in 2h:** <Yes/No; actual time>
- **Items understandable:** <Yes/Partially/No; notes>
- **Evidence links useful:** <Yes/Partially/No; notes>
- **Clusters specific/abstract:** <Mostly specific/Mixed/Mostly abstract; examples>
- **Scoring helpful/distracting:** <Helped/Neutral/Distracted; why>
- **Source Quality Report helpful:** <Yes/Partially/No; notes>
- **Manual trash sorting:** <Yes/Some/No; approximate noise %>
- **Improvements for Cycle 2:** <free text>
```

---

## 13. Quality Flags During Review

During review, the founder should mark if an item suffers from any of the following quality issues. These flags inform the Noise and Quality Analysis (roadmap item 9).

### 13.1 Quality Flag Definitions

| # | Flag | Description | Indicates |
|---|------|-------------|-----------|
| Q1 | `too_abstract` | Pain pattern or opportunity is too abstract to act on | Clustering or opportunity framing quality issue |
| Q2 | `too_generic` | Pain is obvious or generic; "everyone knows this" | Noise filter issue; query may be too broad |
| Q3 | `unclear_buyer` | Actor/ICP is not identifiable from the evidence | Signal extraction quality issue; pain decomposition incomplete |
| Q4 | `unclear_workflow` | Workflow is not described or is too vague | Signal extraction quality issue |
| Q5 | `weak_evidence` | Evidence is thin, low-detail, or unconvincing | Source quality issue; query or repo selection may need tuning |
| Q6 | `single_source_only` | All evidence comes from one source | Source diversity insufficient; may need cross-source validation |
| Q7 | `low_business_relevance` | Pain does not suggest a viable business | ICP alignment issue; query themes may need adjustment |
| Q8 | `too_technical` | Pain is an implementation detail, not a business problem | Signal classification issue; technical curiosity vs. business pain |
| Q9 | `likely_self_promo` | Evidence appears to be vendor promotion, not genuine pain | Noise filter issue; self-promotion detection may need improvement |
| Q10 | `likely_one_off` | Pain is a single incident, not a recurring pattern | Recurrence detection issue; may be legitimate but insufficient for clustering |
| Q11 | `legal_ethical_concern` | Pain domain raises legal or ethical concerns | Excluded market list may need expansion |
| Q12 | `not_founder_fit` | Domain is outside founder expertise or interest | ICP profile alignment issue; founder focus may need refinement |

### 13.2 Flag Recording

For each reviewed item, record any applicable quality flags:

```
Quality flags: <flag1, flag2, ...> or "none"
```

Multiple flags may apply to a single item. Flag count and distribution inform the Noise and Quality Analysis.

---

## 14. Go/No-Go Preparation

After all items are reviewed, the founder should summarize the findings to prepare inputs for the formal Go/No-Go decision (roadmap item 10).

### 14.1 Go/No-Go Input Summary

The following summary must be prepared:

| # | Input | Description |
|---|-------|-------------|
| 1 | **PROMOTE count** | Number of items promoted; names/titles of promoted items |
| 2 | **Candidates worth validation** | Number of items with clear validation path and founder commitment |
| 3 | **Banal/noise count** | Number of items KILLED as banal/noise; approximate % of total reviewed |
| 4 | **Source quality by source** | Per-source assessment: which source produced signal vs. noise |
| 5 | **Scoring alignment with founder** | Match rate and alignment observations |
| 6 | **Review burden** | Summary of burden assessment (was review manageable?) |
| 7 | **1–2 real opportunities?** | Are there at least 1–2 opportunities worth validating? |

### 14.2 Go/No-Go Input Format

```markdown
## Go/No-Go Decision Inputs

### Quantitative Summary
- **PROMOTE:** N items
- **PARK:** N items
- **KILL:** N items (N% of total)
- **NEEDS_MORE_EVIDENCE:** N items
- **REVISIT_LATER:** N items
- **Total reviewed:** N items

### Top Opportunities (PROMOTEd)
1. <title> — score: X.XX, source_diversity: N, validation: <action>
2. ...

### Source Quality
- **Hacker News:** signal_rate=X%, noise_rate=Y%, main noise: <categories>
- **GitHub Issues:** signal_rate=X%, noise_rate=Y%, main noise: <categories>

### Scoring Alignment
- Match rate: N%
- Key observations: <notes>

### Review Burden
- Review took: <time>
- Manageable: Yes/No
- Key friction: <notes>

### Real Opportunities?
- At least 1–2 opportunities worth validating? Yes / No
- If Yes, which ones:
  1. <title>
  2. <title>
```

### 14.3 Decision Direction Guidance

Based on the Go/No-Go inputs, the review should indicate a direction:

| Direction | Indicators |
|-----------|------------|
| **Likely GO** | 1–2+ PROMOTE items with specific pain, clear ICP, and reachable validation; noise <60%; review manageable; scoring aligned |
| **Likely CONDITIONAL GO** | Some interesting items but significant noise (60–80%); scoring partially misaligned; review somewhat burdensome; quality issues identified but fixable |
| **Likely NO-GO** | Zero PROMOTE items; >80% noise; banal/abstract clusters; scoring contradicts founder judgment; broken traceability; review was trash sorting |

This direction is **advisory**, not a decision. The formal Go/No-Go decision is made in roadmap item 10.

---

## 15. Do-Not-Do Rules

During founder review, the following actions are **forbidden**:

| # | Rule | Rationale |
|---|------|-----------|
| DND-1 | **Do not approve source expansion ad hoc** | Source expansion requires a Go decision and explicit roadmap (v2.14+) |
| DND-2 | **Do not mutate portfolio** | Portfolio state is not modified during v2.13 |
| DND-3 | **Do not create `KillReason` records** | `KillReason` artifact creation belongs to a later explicitly approved workflow |
| DND-4 | **Do not treat system recommendation as final** | System recommendations are advisory only; founder decision is authoritative |
| DND-5 | **Do not ignore broken traceability** | If `validation_summary.json` shows traceability failures, do not proceed to review; escalate |
| DND-6 | **Do not proceed if `validation_summary.is_valid` is not `true`** | Review requires a validated pilot run; escalate if validation failed |
| DND-7 | **Do not validate ideas without source evidence** | Every opportunity candidate must trace back to real source evidence |
| DND-8 | **Do not commit runtime review notes** | Review notes are runtime artifacts; they must not be committed unless AG-5 explicitly approves |
| DND-9 | **Do not skip items** | Every item in the review package must receive a decision and notes |
| DND-10 | **Do not make decisions based on title alone** | Read the pain pattern, evidence links, and score components before deciding |

---

## 16. Definition of Done

Item 7 (Founder Review Protocol) is done when:

- [ ] **16.1** Founder Review Protocol exists at `docs/decisions/founder_review_protocol_v2_13.md`.
- [ ] **16.2** Review inputs are listed (Section 2): mandatory inputs, optional deeper-inspection inputs, reference documents.
- [ ] **16.3** Review order is defined (Section 4): 10 steps in order with enforcement rules.
- [ ] **16.4** Decision definitions are explicit (Section 6): 5 decision types with criteria, summary table, recording format.
- [ ] **16.5** Required founder notes are defined (Section 7): 7 note fields with marker definitions and rationale writing rules.
- [ ] **16.6** Validation actions are defined (Section 8): 8 allowed actions with decision-to-action mapping.
- [ ] **16.7** Review scoring rubric exists (Section 9): 10 dimensions with 0–2 scoring, interpretation, and worksheet.
- [ ] **16.8** System alignment check exists (Section 10): 3 alignment categories, recording format, alignment summary, analysis guidance.
- [ ] **16.9** Review output format is defined (Section 11): session header, summary, per-item records, alignment summary, top opportunities, killed summary, follow-up actions.
- [ ] **16.10** Review burden assessment is defined (Section 12): 8 questions, burden thresholds, recording format.
- [ ] **16.11** Quality flags during review are defined (Section 13): 12 flags with recording format.
- [ ] **16.12** Go/No-Go preparation is defined (Section 14): 7 inputs, input format, decision direction guidance.
- [ ] **16.13** Do-not-do rules are defined (Section 15): 10 forbidden actions with rationales.
- [ ] **16.14** Purpose, timebox, and review item inspection fields are defined (Sections 1, 3, 5).
- [ ] **16.15** `.\scripts\dev-git-check.ps1` passes.
- [ ] **16.16** One local commit exists with message: `[v2.13] 7 define founder review protocol`.

---

## 17. References

- [Founder ICP and Preference Profile v2.13](founder_icp_preference_profile_v2_13.md) — baseline for ICP, preferences, rubric, and decision guidance
- [Pilot Cycle 1 Brief v2.13](pilot_cycle_1_brief_v2_13.md) — success/failure criteria, timebox, decision outcomes, approval gates
- [Pilot Run Procedure v2.13](pilot_run_procedure_v2_13.md) — handoff to founder review (Section 13), validation checks, artifact verification
- [Operational Discovery Pilot Run Contract](../contracts/operational_discovery_pilot_run_contract.md) — pilot run lifecycle, founder review loop, Go/No-Go criteria
- [PainCluster Contract](../contracts/pain_cluster_contract.md) — cluster schema, scoring formula, status lifecycle, promotion rules
- [OOS Roadmap v2.13 Checklist](../roadmaps/OOS_roadmap_v2_13_operational_pilot_go_no_go_checklist.md) — parent roadmap

---

## 18. Self-Audit Checklist

- [x] **Title and status present** (header): Title, status, roadmap item, branch, based-on references
- [x] **Purpose stated** (Section 1): What this protocol is and is not
- [x] **Review inputs listed** (Section 2): 6 mandatory inputs, 3 optional inputs, 3 reference documents
- [x] **Review timebox defined** (Section 3): 4 timing rules, session split, time management rules
- [x] **Review order defined** (Section 4): 10 steps in order with enforcement rules
- [x] **Review item fields defined** (Section 5): 20 inspection fields with what-to-check guidance
- [x] **Founder decisions defined** (Section 6): 5 decision types with criteria, summary table, recording format
- [x] **Required founder notes defined** (Section 7): 7 note fields, 4 marker definitions, rationale writing rules with examples
- [x] **Validation actions defined** (Section 8): 8 allowed actions with decision-to-action mapping and detail guidance
- [x] **Founder judgment scoring rubric exists** (Section 9): 10 dimensions with 0–2 scoring, interpretation table, worksheet
- [x] **System alignment check exists** (Section 10): 3 alignment categories, recording format, alignment summary, analysis guidance
- [x] **Review output format defined** (Section 11): 7 sections with formats and artifact policy
- [x] **Review burden assessment defined** (Section 12): 8 questions, burden thresholds, recording format
- [x] **Quality flags defined** (Section 13): 12 flags with recording format
- [x] **Go/No-Go preparation defined** (Section 14): 7 inputs, input format, decision direction guidance
- [x] **Do-not-do rules defined** (Section 15): 10 forbidden actions with rationales
- [x] **Definition of Done present** (Section 16): 16 completion criteria
- [x] **References present** (Section 17): 6 referenced documents
- [x] **No implementation directives**: Document is operational review protocol only
- [x] **No founder decision artifacts created**: Protocol defines process only
- [x] **No `KillReason` records created**: KILL rationale is recorded in review notes only
- [x] **No portfolio mutation**: Portfolio state is not modified
- [x] **No source expansion approval**: Source expansion requires Go decision
- [x] **No source code, test, script, or artifact modifications**
- [x] **All 17 required sections from the task specification are present**

---

*Founder Review Protocol v2.13. Operational review procedure document. Defines the review process and required founder notes only. Does not create founder decision artifacts, KillReason records, or portfolio mutations. Does not modify source code, tests, scripts, or pipeline behavior.*
