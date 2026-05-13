# OOS v2.13 — Pilot Cycle 1 Brief

**Title:** OOS v2.13 — Pilot Cycle 1 Brief
**Status:** Draft / operational brief
**Roadmap item:** v2.13 item 2 — Pilot Cycle 1 Brief
**Branch:** `ops/v2-13-operational-pilot-cycle-1`
**Created:** 2026-05-13
**Based on:**
- v2.12 Operational Discovery Pilot ready state
- v2.13 Founder ICP and Preference Profile ([`founder_icp_preference_profile_v2_13.md`](founder_icp_preference_profile_v2_13.md))

---

## 1. Mission Statement

Pilot Cycle 1 exists to answer a single question:

> **"Does OOS surface useful, specific, business-relevant opportunity candidates from HN + GitHub Issues?"**

This is **not**:
- A source expansion test.
- A production deployment.
- An automated investment or business decision.

This **is**:
- A controlled operational pilot.
- A structured test of the v2.12 pipeline with bounded inputs from two primary sources.
- An evidence-gathering exercise to inform a Go/No-Go decision.

---

## 2. Source Scope

### Primary Sources (included by default)

| Source | Source ID | Source Type | Status |
|--------|-----------|-------------|--------|
| Hacker News | `hacker_news` | `discussion` | Primary; requires live-collection founder approval |
| GitHub Issues | `github_issues` | `issue_tracker` | Primary; requires live-collection founder approval and repo allowlist |

### Optional / Stretch

| Source | Source ID | Source Type | Status |
|--------|-----------|-------------|--------|
| Stack Exchange / Stack Overflow | `stack_exchange` / `stack_overflow` | `q_and_a` | **Excluded by default.** Requires explicit founder approval to include. |

### Explicitly Excluded

The following sources are **out of scope** for Pilot Cycle 1. Their presence in any pilot input or output is a gate violation:

| Source | Source ID | Reason |
|--------|-----------|--------|
| Product Hunt | `product_hunt` | Deferred to v2.14+ (conditional on Go) |
| pimenov.ai | `pimenov_ai` | Deferred to v2.14+ (conditional on Go) |
| Reddit | `reddit` | Deferred to v2.14+ (conditional on Go) |
| Discord | `discord` | Deferred to v2.14+ (conditional on Go) |
| Slack | `slack` | Deferred to v2.14+ (conditional on Go) |
| X / Twitter | `x_twitter` / `twitter` / `x` | Deferred to v2.14+ (conditional on Go) |
| AlternativeTo | `alternative_to` | Deferred to v2.14+ (conditional on Go) |
| YC / Crunchbase | `yc` / `y_combinator` / `crunchbase` | Deferred to v2.14+ (conditional on Go) |
| App marketplaces | — | Deferred to v2.14+ (conditional on Go) |
| Job boards | — | Deferred to v2.14+ (conditional on Go) |
| Blogs / newsletters | — | Deferred to v2.14+ (conditional on Go) |
| Broad scraping | `broad_web_crawl` | Deferred; scope violation |

---

## 3. Pilot Focus Themes

The following pain domains are the primary focus for Pilot Cycle 1. Clusters and candidates in these areas should receive extra attention during review. These are derived from the [Founder ICP and Preference Profile](founder_icp_preference_profile_v2_13.md), Section 10.

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

## 4. Evidence Volume Targets

### Operational Run Targets

These are the expected volumes for a full operational pilot run:

| Artifact | Target | Minimum |
|----------|--------|---------|
| Raw evidence items | 50–150 | 50 |
| Candidate signals | 10–30 | 10 |
| Pain clusters | 3–7 | 3 |
| Opportunity candidates | 3–5 | 3 |
| Ideas worth real validation | 1–2 | 1 |

### First-Cycle Flexibility

If live collection is not yet approved, a smaller bounded / manual input cycle is acceptable.

**Dry cycle minimum:**

| Artifact | Minimum | Notes |
|----------|---------|-------|
| Raw evidence items | 10–25 | Fixture-prepared or manually assembled |
| Candidate signals | 3–10 | Proportionate to evidence volume |
| Pain clusters | 2–4 | Includes cross-source where possible |
| Opportunity candidates | 1 | OR a documented reason why none emerged |

A dry cycle that produces zero opportunity candidates is not automatically a failure — but it requires a documented explanation of why no candidate emerged (e.g., evidence too thin, thematic mismatches, excessive noise).

---

## 5. Success Criteria

Pilot Cycle 1 is **successful** if:

| # | Criterion | Threshold |
|---|-----------|-----------|
| SC-1 | **Actionable opportunity candidates** | At least 1–2 opportunity candidates are specific enough to consider interviews, manual research, or a landing page test |
| SC-2 | **Clean traceability** | Every candidate signal traces to a real `http(s)://` `source_url`; zero placeholder or missing URLs |
| SC-3 | **Manageable founder review** | Founder review completes within 1–2 hours of focused time |
| SC-4 | **Diagnosable noise** | Noise is below 60% of evidence, OR noise is above 60% but the Source Quality Report clearly identifies which sources/queries/themes produce it |
| SC-5 | **Useful Source Quality Report** | Report identifies useful vs. noisy sources/queries and provides actionable tuning guidance |
| SC-6 | **Non-banal clusters** | Pain clusters are specific, not generic ("people want faster software", "AI is changing everything") |
| SC-7 | **Scoring aligns with founder judgment** | Majority of scored items match founder's qualitative assessment (no systematic divergence) |

---

## 6. Failure Criteria

Pilot Cycle 1 **fails** if:

| # | Criterion | Detail |
|---|-----------|--------|
| FC-1 | **Overwhelming noise** | 80–90%+ of outputs are noise (banal, irrelevant, promotional) |
| FC-2 | **Generic opportunity candidates** | Candidates are abstract/vague: "an AI-powered platform for developers", "a better DevOps tool" |
| FC-3 | **Founder review is trash sorting** | Review provides no learning, no useful output, high burden — founder is manually discarding irrelevant items |
| FC-4 | **Scoring contradicts founder judgment** | Systematic divergence: high-scored items are banal, interesting items are scored low |
| FC-5 | **Broken traceability** | Placeholder URLs, missing evidence chains, unresolvable sources |
| FC-6 | **No idea worth validating** | Nothing passes the "would I test this?" threshold |
| FC-7 | **Source quality report is useless** | Metrics exist but provide no actionable insight for decision-making |

If the pilot fails, the system must **not** proceed to source expansion. The Go/No-Go decision must route to pipeline repair.

---

## 7. Timebox

| Phase | Duration | Notes |
|-------|----------|-------|
| Preparation | 1 day | Brief finalization, query plan design, allowlist definition |
| Bounded collection / input preparation | 1–2 days | Manual assembly, fixture preparation, or live collection with founder approval |
| Pilot run and artifact verification | Same day as input ready | Run orchestrator, verify all outputs, confirm traceability |
| Founder review | 1–2 days | Max 2 hours active review time per founder |
| Decision and report | Same day after review | Produce Go/No-Go decision and results report |
| **Total cycle max** | **7 calendar days** | From preparation start to decision recorded |

If any phase exceeds its allotment, that is a signal to document operational friction in the pilot results report.

---

## 8. Expected Outputs

Pilot Cycle 1 must produce the following artifacts. All runtime outputs must use an explicit caller-provided `output_dir`. No artifacts may be written to default repository paths.

| # | Artifact | Format | Description |
|---|----------|--------|-------------|
| O-1 | Raw evidence package | `raw_evidence.json` (or equivalent `.jsonl`) | Bounded input evidence items with `source_id`, `source_type`, `source_url` |
| O-2 | Candidate signals | `candidate_signals.json` | Extracted signals with scores and source traceability |
| O-3 | Pain clusters | `pain_clusters.json` | Synthesized clusters with member signals and scores |
| O-4 | Source quality report (JSON) | `source_quality_report.json` | Machine-readable quality metrics per source/query |
| O-5 | Source quality report (Markdown) | `source_quality_report.md` | Human-readable quality summary with recommendations |
| O-6 | Founder review package (JSON) | `founder_review_package.json` | Structured package for founder review: top clusters, candidates, traceability |
| O-7 | Founder review package (Markdown) | `founder_review_package.md` | Human-readable review package |
| O-8 | Validation summary | `validation_summary.json` | Pipeline validation: format checks, traceability pass/fail, source scope compliance |
| O-9 | Pilot run manifest | `pilot_run_manifest.json` | Timestamp, parameters, sources used, evidence counts, pipeline version |
| O-10 | Pilot results report | `pilot_results_report_v2_13.md` | Aggregated report: quantitative metrics, qualitative observations, Go/No-Go recommendation |
| O-11 | Founder review notes | `founder_review_notes_v2_13.md` | Structured review notes with decisions, rationales, and markers |
| O-12 | Go/No-Go decision | `go_no_go_decision_v2_13.md` | Formal decision with rationale and next-step direction |

### Artifact Policy

- **No committed repository artifacts unless explicitly approved.** The repository must not accumulate unapproved runtime outputs.
- **All runtime outputs must use explicit caller-provided `output_dir`.** The pilot orchestrator writes artifacts only when the caller supplies a destination directory.
- **Final dev ledger reports may be committed only in the final checkpoint** (v2.13 item 11) if the roadmap item explicitly allows them.
- **Interim validation reports must not be committed.**

---

## 9. Founder Review Deadline

- Founder review should happen **within 48 hours** after pilot outputs are generated and the founder review package is delivered.
- Review session target: **maximum 2 hours** of active review time.
- If review takes longer than 2 hours, that is a signal of a review package quality problem and should be documented in the pilot results report as operational friction.

---

## 10. Founder Review Required Decisions

For each top-ranked cluster and opportunity candidate presented in the review package, the founder must assign one of five decisions:

| Decision | Meaning | When to Use |
|----------|---------|-------------|
| **PROMOTE** | Opportunity worth real validation | Specific pain, clear ICP, business cost visible, plausible validation path, founder interest |
| **PARK** | Interesting but not now | Moderate interest, unclear monetization, timing not right, or not aligned with current focus |
| **KILL** | Not worth pursuing | Banal/generic, no buyer, excluded market, vendor promo, no validation path |
| **NEEDS_MORE_EVIDENCE** | Promising but insufficient data | Interesting pain, thin evidence, single-source, or missing willingness-to-pay signal |
| **REVISIT_LATER** | Check again after more cycles | Possibly interesting, market not ready, needs source expansion, or depends on external trends |

### Required per Decision

Each decision must include:

1. **One-sentence rationale** — why this decision was made.
2. **Quality marker** — exactly one of:
   - `interesting` — worth the founder's attention
   - `banal` — generic, obvious, or low-signal
   - `unclear` — ambiguous, needs more data
   - `actionable` — specific enough to act on
3. **Suggested validation action** (if PROMOTE or NEEDS_MORE_EVIDENCE):
   - `interview` — talk to potential users
   - `landing_page` — test demand with a landing page
   - `manual_research` — deeper manual investigation
   - `collect_more_evidence` — expand source scope for this pain
   - `kill_no_action` — kill with no further action (for KILL decisions only)

### KILL Decision Rules

- KILL decisions require a written founder rationale explaining **why** the idea died, not just labeling it.
- Acceptable rationale categories include: `too_generic`, `no_buyer`, `vendor_promo_false_positive`, `no_real_pain`, `not_aligned`, `excluded_market`, `no_validation_path`, `founder_bottleneck`, `ethical_conflict`.
- This brief does **not** create `KillReason` records or kill archive entries. Any future `KillReason` artifact creation belongs only to a later explicitly approved workflow.

### Decision Guidance Reference

Founder should reference the [Founder ICP and Preference Profile](founder_icp_preference_profile_v2_13.md) for:
- Preferred ICPs (Section 3)
- Preferred opportunity types (Section 4)
- Excluded markets (Section 5)
- Business relevance signals (Section 6)
- Noise/banal definitions (Section 7)
- Review rubric questions R-1 through R-10 (Section 8)
- Decision guidance criteria (Section 9)

---

## 11. Approval Gates

The following explicit founder approvals are **required** before the corresponding action. These gates are enforced; no work proceeds past a gate without approval.

| # | Gate | Description |
|---|------|-------------|
| AG-1 | **Live HN collection** | Must not be default; explicit founder opt-in required before any live Hacker News API calls |
| AG-2 | **Live GitHub Issues collection** | Must not be default; explicit founder opt-in required before any live GitHub API calls |
| AG-3 | **GitHub repo allowlist** | Founder must review and approve the specific repositories before collection begins |
| AG-4 | **Stack Exchange stretch** | Must not be included in default pilot path; requires explicit founder approval |
| AG-5 | **Committing runtime pilot artifacts** | No runtime outputs committed to repository without explicit founder approval |
| AG-6 | **Starting any source expansion** | No additional sources beyond HN + GitHub Issues (and optionally Stack Exchange if approved) may be added to the pilot |
| AG-7 | **Go/No-Go decision finalization** | The decision is founder-made, evidence-supported; it must not be automated |

### Approval Gate Timing

| Gate | When Required |
|------|---------------|
| AG-1, AG-2, AG-3 | Before Pilot Input Preparation (v2.13 item 5) |
| AG-4 | Before Pilot Input Preparation if stretch is desired |
| AG-5 | After pilot run, before committing outputs |
| AG-6 | Anytime before source expansion (enforced by scope) |
| AG-7 | After founder review, before finalizing v2.13 |

---

## 12. Operational Constraints

The following constraints are binding for Pilot Cycle 1:

| # | Constraint |
|---|------------|
| C-1 | No live API calls in tests |
| C-2 | No LLM validation in default tests |
| C-3 | No broad scraping — collection is query-bounded |
| C-4 | No deferred sources in pilot inputs or outputs |
| C-5 | No automated founder decisions |
| C-6 | No portfolio mutation — OOS portfolio state is not modified |
| C-7 | No `KillReason` artifact creation — decisions are recorded in review notes only |
| C-8 | No production deployment |
| C-9 | No UI / dashboard work |
| C-10 | No database / server architecture changes |
| C-11 | No source code, test, script, or example modifications (this is a docs-only operational item) |

---

## 13. Decision Outcomes

Based on pilot results and founder review, one of three outcomes will be recorded:

### GO

**Criteria:** Pilot produces 1–2 genuinely interesting, actionable opportunity candidates with clean traceability and manageable noise.

**Next step:** Proceed to second pilot cycle or cautious source expansion planning. Evaluate Stack Exchange inclusion. Begin planning controlled source expansion.

### CONDITIONAL GO

**Criteria:** Some interesting signals exist, but quality, scoring, or filtering needs improvement. Noise is elevated but diagnostic. Founder review produced insights but was somewhat burdensome.

**Next step:** Proceed to **v2.14 Pilot Quality Improvements**. Implement fixes identified in Noise and Quality Analysis, tune scoring weights, improve clustering, reduce review burden. Re-run pilot after fixes.

### NO-GO

**Criteria:** Overwhelming noise (80–90%+), banal clusters, abstract candidates, broken traceability, scoring contradicts founder judgment, no idea worth validating.

**Next step:** Proceed to **Core Discovery Pipeline Repair**. Diagnose root causes, fix scoring/clustering/traceability, reconsider source strategy and ICP alignment. Do **not** expand sources.

---

## 14. Risks

| # | Risk | Likelihood | Mitigation |
|---|------|------------|------------|
| R-1 | HN/GitHub may overrepresent developer pain, underrepresent SMB/finance/operations pain | Medium | Focus themes (Section 3) include non-dev domains; document bias in results report |
| R-2 | GitHub repo allowlist may bias results toward specific project ecosystems | Medium | Choose allowlist repos across multiple pain domains; document allowlist selection rationale |
| R-3 | HN may produce hype/noise (launch posts, trend threads, flamewars) | High | Query filtering, noise definitions from ICP profile, Source Quality Report identifies noise rate per query |
| R-4 | Founder preferences may be too narrow for initial evidence volume | Medium | First-cycle flexibility (Section 4) allows smaller dry cycle; document gaps for v2.14 |
| R-5 | Scoring may over/underweight business relevance for HN + GitHub evidence | Medium | Compare scoring against founder judgment; divergence is a documented failure criterion |
| R-6 | Evidence volume may be too small for strong conclusions | Medium | Dry cycle minimum is documented; "no conclusion" is an acceptable output if explained |
| R-7 | Timebox may be insufficient if manual input preparation is unexpectedly large | Low | Dry cycle has bounded expectations; if preparation exceeds 2 days, document as operational friction |

---

## 15. Definition of Done

Item 2 (Pilot Cycle 1 Brief) is complete when:

- [x] Pilot brief exists at `docs/decisions/pilot_cycle_1_brief_v2_13.md`
- [x] Source scope is explicit: HN + GitHub Issues primary; Stack Exchange stretch; all others excluded
- [x] Evidence targets are explicit: operational targets (50–150 evidence, 10–30 signals, 3–7 clusters, 3–5 candidates, 1–2 ideas) and dry cycle minimums
- [x] Success criteria are explicit: 7 criteria with thresholds
- [x] Failure criteria are explicit: 7 criteria with details
- [x] Timebox is explicit: 7 calendar days max, per-phase breakdown
- [x] Expected outputs are listed: 12 artifacts with formats and descriptions
- [x] Founder review deadline is defined: 48 hours, max 2 hours active review
- [x] Approval gates are listed: 7 gates with timing
- [x] Decision outcomes are defined: GO, CONDITIONAL GO, NO-GO with criteria and next steps
- [x] Risks are identified: 7 risks with likelihood and mitigation
- [x] Operational constraints are explicit: 11 binding constraints
- [ ] `.\scripts\dev-git-check.ps1` passes
- [ ] One local commit exists with message: `[v2.13] 2 define pilot cycle brief`

---

## 16. References

- [Founder ICP and Preference Profile v2.13](founder_icp_preference_profile_v2_13.md) — baseline for ICP, preferences, rubric, and decision guidance
- [OOS Roadmap v2.13 Checklist](../roadmaps/OOS_roadmap_v2_13_operational_pilot_go_no_go_checklist.md) — parent roadmap
- [Operational Discovery Pilot Run Contract](../contracts/operational_discovery_pilot_run_contract.md) — pilot run contract from v2.11
- [OOS Roadmap v2.12 Checklist](../roadmaps/OOS_roadmap_v2_12_operational_discovery_pilot_checklist.md) — predecessor roadmap

---

*Pilot Cycle 1 Brief v2.13. Operational planning document. Does not modify source code, tests, scripts, or pipeline behavior.*
