# OOS v2.13 — Go / Conditional Go / No-Go Decision Framework

**Title:** OOS v2.13 — Go / Conditional Go / No-Go Decision Framework
**Status:** Draft / operational decision framework
**Roadmap item:** v2.13 item 10
**Branch:** `ops/v2-13-operational-pilot-cycle-1`
**Created:** 2026-05-13
**Schema version:** `go_no_go_decision_framework.v1`

**Based on:**
- [Founder ICP Preference Profile v2.13](founder_icp_preference_profile_v2_13.md) — item 1
- [Pilot Cycle 1 Brief v2.13](pilot_cycle_1_brief_v2_13.md) — item 2
- [Founder Review Protocol v2.13](founder_review_protocol_v2_13.md) — item 7
- [Pilot Results Report Template v2.13](pilot_results_report_template_v2_13.md) — item 8
- [Noise and Quality Analysis Framework v2.13](noise_quality_analysis_framework_v2_13.md) — item 9

---

## 1. Purpose

The purpose of this framework is to decide whether the Operational Discovery Pilot is useful enough to **continue, improve, or stop**.

This framework answers:

1. **Did OOS find useful business-relevant opportunities?**
2. **Were the opportunities specific and traceable?**
3. **Was founder review useful and manageable?**
4. **Was the noise level acceptable or diagnosable?**
5. **Should the next roadmap be second pilot / source expansion, quality improvements, or core repair?**

### 1.1 What This Framework Is

- A structured decision process defining required evidence, thresholds, scoring, procedure, and record structure.
- The authoritative mapping from pilot evidence to GO / CONDITIONAL GO / NO-GO outcome.
- The bridge between all v2.13 pilot artifacts and the v2.14 roadmap direction.

### 1.2 What This Framework Is Not

- The actual Go/No-Go decision. The decision is made only after the pilot run, founder review, and noise/quality analysis are complete.
- A populated decision record. This framework defines the record structure; the populated record is a runtime/output artifact.
- Automated decision-making. The framework provides advisory scoring; the founder makes the final decision.
- Source code, test, script, or artifact modification.
- A pilot run authorization.
- A `KillReason` record.
- A portfolio mutation.
- A source expansion approval.

---

## 2. Required Inputs

The Go/No-Go decision must be based on the following inputs. All inputs must be available and verified before the decision procedure begins.

### 2.1 Mandatory Inputs

| # | Input | Format | Source Item | Description |
|---|-------|--------|-------------|-------------|
| 1 | `pilot_results_report_v2_13.md` | Markdown | Item 8 | Aggregated pilot results with all 12 required sections, metrics, and criteria checks |
| 2 | `founder_review_notes_v2_13.md` | Markdown | Item 7 | Structured review notes with decisions, rationales, markers, alignment data, and burden assessment |
| 3 | `noise_quality_analysis_output` | YAML/JSON/Markdown | Item 9 | Structured noise and quality analysis per the framework (Section 11 output schema) |
| 4 | `source_quality_report.json` | JSON | Item 6 | Machine-readable quality metrics per source/query/repo |
| 5 | `source_quality_report.md` | Markdown | Item 6 | Human-readable quality summary with recommendations |
| 6 | `founder_review_package.json` | JSON | Item 6 | Structured review package with cluster scores, evidence links, advisory recommendations |
| 7 | `founder_review_package.md` | Markdown | Item 6 | Human-readable review package |
| 8 | `validation_summary.json` | JSON | Item 6 | Pipeline validation: `is_valid` must be `true` |
| 9 | `pilot_run_manifest.json` | JSON | Item 6 | Run metadata: parameters, counts, approvals, limitations |
| 10 | `pain_clusters.json` | JSON | Item 6 | Full cluster data: pain patterns, scores, evidence lists |
| 11 | `candidate_signals.json` | JSON | Item 6 | Full candidate signal list with scores and traceability |

### 2.2 Reference Documents (Read-Only)

| # | Document | Purpose |
|---|----------|---------|
| R1 | [Founder ICP Preference Profile v2.13](founder_icp_preference_profile_v2_13.md) | ICP definitions, excluded markets, relevance signals, noise definitions, review rubric |
| R2 | [Pilot Cycle 1 Brief v2.13](pilot_cycle_1_brief_v2_13.md) | Success/failure criteria, timebox, evidence volume targets, decision outcomes |
| R3 | [Founder Review Protocol v2.13](founder_review_protocol_v2_13.md) | Decision definitions, scoring rubric, alignment check, burden assessment |
| R4 | [Pilot Results Report Template v2.13](pilot_results_report_template_v2_13.md) | Report structure, metrics definitions, criteria check format |
| R5 | [Noise and Quality Analysis Framework v2.13](noise_quality_analysis_framework_v2_13.md) | Noise taxonomy, quality thresholds, source/cluster/scoring analysis dimensions |

---

## 3. Decision Authority

The following rules define who and what can make or influence the Go/No-Go decision:

| # | Rule |
|---|------|
| **DA-1** | The Go/No-Go decision is **founder-made**. No system, script, or automated process makes the final decision. |
| **DA-2** | Automated scoring cannot make the final decision. Scores and matrices are advisory only. |
| **DA-3** | System recommendation (from the pilot results report Section 12 or this framework's scoring matrix) is **advisory only**. |
| **DA-4** | No source expansion is approved automatically. A GO decision enables *planning* for source expansion; it does not auto-execute it. |
| **DA-5** | No portfolio mutation happens in this decision. Portfolio state is not modified. |
| **DA-6** | No `KillReason` records are created by this framework. Kill rationale is recorded in founder review notes only. |
| **DA-7** | If the founder disagrees with the advisory recommendation, the founder's decision is authoritative. The disagreement and rationale must be recorded. |
| **DA-8** | The decision is binding for roadmap direction. A GO decision means the next roadmap is second pilot or source expansion planning. A CONDITIONAL GO means v2.14 Pilot Quality Improvements. A NO-GO means Core Discovery Pipeline Repair. |

---

## 4. Decision Outcomes

Exactly three outcomes are possible. No variations, no sub-outcomes, no deferred decisions.

### 4.1 GO

**Definition:** Pilot produced enough value to continue. The pipeline is working well enough to justify continued investment and cautious next steps.

**Next step:** Second pilot cycle or cautious source expansion planning.

**What GO means:**
- OOS found at least 1–2 business-relevant, specific, traceable opportunities.
- The opportunities are worth real-world validation within 1–2 weeks.
- Noise is manageable or clearly diagnosable.
- Founder review was useful, not burdensome.
- Scoring reasonably aligns with founder judgment.
- The Source Quality Report provides actionable tuning guidance.

**What GO does NOT mean:**
- Automatic source expansion. Sources are added only through explicit v2.14+ roadmap items.
- The pipeline is perfect. Quality improvements may still be scoped, but they are refinements, not repairs.
- Every cluster was useful. Noise is expected; the signal-to-noise ratio is acceptable.

### 4.2 CONDITIONAL GO

**Definition:** Pilot produced some value but quality problems must be fixed before proceeding to source expansion or a second pilot.

**Next step:** v2.14 Pilot Quality Improvements.

**What CONDITIONAL GO means:**
- At least one interesting opportunity exists but evidence is thin or quality issues are significant.
- Noise is elevated (60–80%) but specific sources/queries/components can be identified as problems.
- Scoring is partially misaligned with founder judgment but patterns are identifiable and fixable.
- Founder review was somewhat burdensome but produced useful insights.
- The path to fixing quality issues is clear and scoped.

**What CONDITIONAL GO does NOT mean:**
- The pipeline is ready for source expansion. Quality fixes come first.
- A "maybe later" — CONDITIONAL GO is an active commitment to fix quality in v2.14 and re-evaluate.
- Source expansion can happen in parallel with quality fixes. It cannot.

### 4.3 NO-GO

**Definition:** Pilot did not produce useful opportunities, or the pipeline quality is too poor to justify continued pilot cycles without fundamental repairs.

**Next step:** Core Discovery Pipeline Repair.

**What NO-GO means:**
- Zero opportunities worth real-world validation.
- Overwhelming noise (>80%) or noise is undiagnosable.
- PainClusters are banal/generic.
- Opportunity candidates are abstract and unactionable.
- Founder review felt like manual trash sorting.
- Scoring systematically contradicts founder judgment.
- Traceability is broken for important candidates.
- Source Quality Report does not help decision-making.
- Fixes would require rebuilding core pipeline components before another pilot is viable.

**What NO-GO does NOT mean:**
- OOS is abandoned. It means the current pipeline configuration is not working and needs fundamental repair.
- The sources (HN, GitHub) are permanently rejected. After core repair, they may be reconsidered.
- The ICP profile is wrong. It may be fine, but the pipeline cannot extract and score against it effectively.

---

## 5. Quantitative Criteria

### 5.1 GO — Quantitative Criteria

A GO decision is supported when **most** of the following are true:

| # | Criterion | Threshold | Source |
|---|-----------|-----------|--------|
| GQ-1 | PROMOTE candidates | At least 1–2 items with founder PROMOTE decision | `founder_review_notes_v2_13.md` |
| GQ-2 | Candidates worth real validation | At least 1 candidate with clear validation path achievable in 1–2 weeks | `founder_review_notes_v2_13.md` |
| GQ-3 | Noise rate | < 60% of evidence classified as noise, OR noisy parts are clearly isolatable by source/query/repo | `source_quality_report.json`, noise analysis |
| GQ-4 | Traceability failures | Zero for reviewed candidates; zero missing/placeholder URLs across all artifacts | `validation_summary.json` |
| GQ-5 | Founder review time | Completed within 120 minutes | `founder_review_notes_v2_13.md` |
| GQ-6 | System-founder recommendation match | Match or partial match >= 50% across reviewed items | `founder_review_notes_v2_13.md` |
| GQ-7 | Useful source/query/repo | At least 1 source, query bucket, or repo identified as clearly useful | `source_quality_report.md` |
| GQ-8 | Source Quality Report utility | Report helped decision-making — identified useful vs. noisy sources/queries with actionable recommendations | Founder assessment |
| GQ-9 | Specific, non-banal PainCluster | At least 1 PainCluster is specific (clear actor + workflow + object + pain_verb), non-banal, and business-relevant | `founder_review_notes_v2_13.md`, cluster inspection |

**Decision rule:** If 7–9 of GQ-1 through GQ-9 are met, the quantitative evidence strongly supports GO. If 5–6 are met, GO may still be supported but qualitative criteria and the scoring matrix should be weighed more heavily.

### 5.2 CONDITIONAL GO — Quantitative Criteria

A CONDITIONAL GO decision is supported when:

| # | Criterion | Threshold | Source |
|---|-----------|-----------|--------|
| CQ-1 | Interesting opportunity exists | At least 1 item with founder PROMOTE or NEEDS_MORE_EVIDENCE with plausible pain | `founder_review_notes_v2_13.md` |
| CQ-2 | Noise rate | 60–80% overall, but specific noise sources/queries/components are identified and tunable | `source_quality_report.json`, noise analysis |
| CQ-3 | Scoring alignment | Scoring partially misaligned with founder judgment (match rate 30–50%) but specific component issues are identified | Scoring calibration analysis (item 9, Section 8) |
| CQ-4 | Cluster quality | Clusters are somewhat useful but need split/merge tuning; specific cluster actions are identified | Cluster-level analysis (item 9, Section 7) |
| CQ-5 | Founder review burden | Review was somewhat burdensome (90–180 minutes) but not hopeless; friction points are identified | `founder_review_notes_v2_13.md` |
| CQ-6 | Tuning actions clear | Specific source/query/repo tuning actions are identified and scoped | Noise analysis (item 9, Section 9) |
| CQ-7 | Traceability | Mostly clean; no fatal traceability failures in top candidates; minor issues are fixable | `validation_summary.json` |

**Decision rule:** CONDITIONAL GO is the default when useful signal exists but quality issues prevent a clean GO. The key discriminator is **diagnosability** — if the problems can be specifically identified and scoped for v2.14 fixes, CONDITIONAL GO is appropriate.

### 5.3 NO-GO — Quantitative Criteria

A NO-GO decision is required when **most** of the following are true:

| # | Criterion | Threshold | Source |
|---|-----------|-----------|--------|
| NQ-1 | Validatable opportunities | Zero — no items with founder PROMOTE; nothing passes the "would I test this?" threshold | `founder_review_notes_v2_13.md` |
| NQ-2 | Noise rate | > 80% of evidence is noise, OR noise is mostly undiagnosable (cannot identify specific sources/queries/components causing it) | `source_quality_report.json`, noise analysis |
| NQ-3 | PainCluster quality | PainClusters are banal/generic ("people want faster software", "AI is changing everything") | `founder_review_notes_v2_13.md` |
| NQ-4 | Opportunity candidate quality | Candidates are abstract ("an AI-powered platform for developers", "a better DevOps tool") | `founder_review_notes_v2_13.md` |
| NQ-5 | Founder review experience | Review felt like manual trash sorting — no learning, no useful output, high burden (>180 minutes or abandoned) | `founder_review_notes_v2_13.md` |
| NQ-6 | Scoring alignment | Scoring systematically disagrees with founder judgment — match rate < 30%, or systematic over-promotion of banal items | Scoring calibration analysis |
| NQ-7 | Traceability | Broken for important candidates — placeholder URLs, missing evidence chains, unresolvable sources | `validation_summary.json` |
| NQ-8 | Source Quality Report utility | Report does not help decision-making — metrics exist but provide no actionable insight | Founder assessment |

**Decision rule:** If 5–8 of NQ-1 through NQ-8 are met, NO-GO is strongly indicated. If only 3–4 are met but they include NQ-1 (zero validatable opportunities) or NQ-2 (>80% undiagnosable noise), NO-GO should still be seriously considered.

---

## 6. Qualitative Criteria

The founder must answer the following qualitative questions. These questions probe dimensions that quantitative metrics alone cannot capture.

| # | Question | What to Consider |
|---|----------|-----------------|
| QL-1 | **Would I spend time validating at least one idea?** | Is there at least one PROMOTE candidate that the founder is genuinely motivated to pursue? If none, why? |
| QL-2 | **Can I explain the buyer and pain in one sentence?** | For the top opportunity: "X struggles with Y because of Z." If this sentence cannot be formed, the opportunity is not specific enough. |
| QL-3 | **Does the evidence make the pain feel real?** | Do the evidence links, quotes, and pain patterns convey authentic user struggle, or do they feel abstract and constructed? |
| QL-4 | **Is there a plausible path to interviews or manual validation?** | Can the founder find and talk to 3–5 people experiencing this pain within 2 weeks? If not, the opportunity is not ready for validation. |
| QL-5 | **Is this aligned with founder preferences?** | Does the opportunity match the ICP profile (Sections 3–5), preferred opportunity types (Section 4), and Pilot Cycle 1 focus themes (Section 10)? |
| QL-6 | **Is this legally and ethically clean?** | No ToS hostility, gray-area scraping, regulatory nightmares, or excluded-market concerns. |
| QL-7 | **Does OOS save me research time compared with manual browsing?** | Would the founder have found these opportunities by browsing HN and GitHub directly? Did OOS surface something non-obvious? |
| QL-8 | **Did the system surface something I might have missed?** | Was there a non-obvious connection, cross-source insight, or surprising pain pattern that the founder would not have discovered alone? |
| QL-9 | **Did the review package reduce or increase cognitive load?** | Was the structured package easier to review than raw browsing, or did the format add friction? |

**Interpretation:**
- **7–9 favorable answers:** Strong qualitative support for GO.
- **4–6 favorable answers:** Mixed qualitative picture; consistent with CONDITIONAL GO.
- **0–3 favorable answers:** Weak qualitative support; consistent with NO-GO.

These answers must be recorded in the decision rationale (Section 10). They are not scored numerically but inform the overall judgment.

---

## 7. Decision Scoring Matrix

The decision scoring matrix is a 0–2 rubric across 10 dimensions. It produces an advisory score that guides the decision but does not replace founder judgment.

### 7.1 Scoring Dimensions

| # | Dimension | 0 | 1 | 2 |
|---|-----------|---|---|---|
| D1 | **Opportunity quality** | No specific, actionable opportunity found. All candidates are abstract or banal. | At least 1 candidate is moderately specific but lacks clear buyer or validation path. | At least 1–2 candidates are specific, have clear buyer, have clear pain, and have reachable validation paths. |
| D2 | **Evidence traceability** | Traceability is broken — missing/placeholder URLs in reviewed candidates, unresolvable sources. | Traceability is mostly clean with minor, fixable issues (1–2 isolated URL problems). | Traceability is clean — zero missing, placeholder, or invalid URLs; every candidate traces to a real `http(s)://` URL. |
| D3 | **Business relevance** | No candidate has clear business cost or buyer. Pains are hobby-only, technical curiosity, or no-business-cost. | At least 1 candidate has implied business cost but cost is not quantified or buyer is unclear. | At least 1–2 candidates have explicit business cost (time, money, risk) and clear, reachable buyers from high/medium priority ICPs. |
| D4 | **Founder interest** | Founder is not interested in any candidate. All feel misaligned, too far from expertise, or not worth time. | Founder is moderately interested in at least 1 candidate — "interesting but not compelling." | Founder is genuinely interested in at least 1–2 candidates and would spend time validating them. |
| D5 | **Review usability** | Review felt like manual trash sorting. Review package was confusing, evidence links not useful, >50% obvious noise. | Review was somewhat burdensome but produced insights. Some friction but manageable. | Review was smooth, manageable within 90 minutes, package was clear and navigable, evidence links were useful. |
| D6 | **Noise manageability** | Noise >80% and undiagnosable — cannot identify specific sources/queries/components causing it. | Noise 60–80% but specific noise sources/queries/components are identified and tunable. | Noise <60% OR noisy parts are clearly isolatable by source/query/repo with clear tuning actions. |
| D7 | **Source quality usefulness** | Source Quality Report provides no actionable insight. Metrics exist but don't help decide what to tune. | Source Quality Report identifies some useful vs. noisy sources/queries but recommendations are vague. | Source Quality Report clearly identifies useful vs. noisy sources/queries/repos with specific, actionable tuning recommendations. |
| D8 | **Scoring alignment** | Scoring systematically contradicts founder judgment. Match rate <30%, or systematic over-promotion of banal items. | Scoring partially aligns (match rate 30–50%). Specific component issues are identified but fixable. | Scoring reasonably aligns with founder judgment. Match rate >=50%, no systematic divergence. |
| D9 | **Validation readiness** | No candidate has a feasible validation path in <1 month. Zero items with clear next-step validation actions. | At least 1 candidate has a plausible validation path but requires significant prep or the path is unclear. | At least 1–2 candidates have clear, feasible validation paths achievable in 1–2 weeks with concrete next steps. |
| D10 | **Operational friction** | The pilot process was broken or unsustainable. Input preparation, execution, verification, or review had systemic failures. | Some operational friction exists but is identifiable and fixable. Specific friction points are documented. | The pilot process ran smoothly. Friction was minimal or expected for a first cycle. No systemic blockers. |

### 7.2 Score Interpretation

| Total Score | Interpretation | Typical Outcome |
|-------------|---------------|-----------------|
| **16–20** | **GO leaning** — Strong evidence that the pipeline is working. | GO |
| **10–15** | **CONDITIONAL GO leaning** — Mixed evidence. Useful signal exists but quality improvements are needed before proceeding. | CONDITIONAL GO |
| **0–9** | **NO-GO leaning** — Weak or negative evidence. The pipeline is not working well enough to continue without fundamental repairs. | NO-GO |

### 7.3 Scoring Rules

1. **Score each dimension independently.** Do not let overall impression drive individual dimension scores.
2. **Score based on evidence from pilot artifacts,** not on assumptions about the pipeline's potential.
3. **If a dimension cannot be scored from available evidence, score it 0** and note the missing information as an open question.
4. **The total score is advisory only.** The founder may choose a different outcome than the matrix indicates. If so, the rationale for diverging must be recorded.
5. **The matrix does not replace the quantitative or qualitative criteria.** It synthesizes them into a single advisory score.

### 7.4 Scoring Worksheet

```
Decision Scoring Matrix — Pilot Cycle 1

| # | Dimension | Score (0/1/2) | Notes |
|---|-----------|---------------|-------|
| D1 | Opportunity quality          |   |                                   |
| D2 | Evidence traceability        |   |                                   |
| D3 | Business relevance           |   |                                   |
| D4 | Founder interest             |   |                                   |
| D5 | Review usability             |   |                                   |
| D6 | Noise manageability          |   |                                   |
| D7 | Source quality usefulness    |   |                                   |
| D8 | Scoring alignment            |   |                                   |
| D9 | Validation readiness         |   |                                   |
| D10 | Operational friction        |   |                                   |
|     | **TOTAL**                   |   |                                   |

Matrix interpretation: ___________ (GO leaning / CONDITIONAL GO leaning / NO-GO leaning)
Founder outcome: ___________ (GO / CONDITIONAL GO / NO-GO)
Matrix matches founder outcome? Yes / No
If No, rationale for divergence: _________________________________
```

---

## 8. Decision Meeting / Review Procedure

The following 12-step procedure must be followed to reach the Go/No-Go decision. Steps must be completed in order. Steps 1–2 are gates.

### Step-by-Step Procedure

| Step | Action | Input | Output |
|------|--------|-------|--------|
| **1** | **Confirm pilot run valid.** Verify `validation_summary.json` shows `is_valid: true`. Verify all expected artifacts are present and complete. | `validation_summary.json`, `pilot_run_manifest.json` | Confirmation: pilot run is valid; all artifacts present. If invalid, escalate — do not proceed. |
| **2** | **Confirm founder review completed.** Verify `founder_review_notes_v2_13.md` exists with all required fields per the Founder Review Protocol. Verify every review item has a decision and rationale. | `founder_review_notes_v2_13.md` | Confirmation: founder review is complete. If incomplete, do not proceed. |
| **3** | **Review Pilot Results Report.** Read the full pilot results report. Understand the funnel, source quality, top clusters, founder decisions, and criteria check results. | `pilot_results_report_v2_13.md` | Understanding of overall pilot results. |
| **4** | **Review Noise and Quality Analysis.** Read the noise and quality analysis output. Understand the noise taxonomy counts, source-level findings, cluster-level findings, scoring calibration findings, and recommended fixes. | `noise_quality_analysis_output` (YAML/JSON/MD) | Understanding of quality problems, their causes, and their fixability. |
| **5** | **Review top 1–2 candidates.** Deep-dive on the highest-potential PROMOTE or NEEDS_MORE_EVIDENCE candidates. Verify: specific pain, clear buyer, business cost, traceability, validation readiness. | `founder_review_notes_v2_13.md`, `pain_clusters.json`, `candidate_signals.json` | Clear picture of the best opportunities the pilot produced. |
| **6** | **Apply quantitative criteria.** Score each quantitative criterion (GQ-1 through GQ-9 for GO; CQ-1 through CQ-7 for CONDITIONAL GO; NQ-1 through NQ-8 for NO-GO). Record which criteria are met and which are not. | Pilot artifacts, Sections 5.1–5.3 of this framework | Quantitative criteria result: counts of met criteria for each outcome. |
| **7** | **Apply qualitative questions.** Answer QL-1 through QL-9 honestly. Record answers. | Founder judgment, pilot artifacts, Section 6 of this framework | Qualitative assessment: 9 answered questions. |
| **8** | **Fill decision scoring matrix.** Score each of the 10 dimensions (D1–D10) 0/1/2. Compute total. Record interpretation. | Pilot artifacts, founder judgment, Section 7 of this framework | Completed scoring matrix with total and interpretation. |
| **9** | **Select GO / CONDITIONAL GO / NO-GO.** Based on quantitative criteria, qualitative questions, and scoring matrix, make the decision. If the three sources of evidence point in different directions, weigh qualitative criteria and founder judgment most heavily. | All above | Outcome: `GO`, `CONDITIONAL GO`, or `NO-GO`. |
| **10** | **Record rationale.** Write a clear rationale for the decision. Cite specific pilot evidence (cluster IDs, metrics, founder decisions, noise categories). Explain why the chosen outcome is correct and why the other outcomes were not chosen. | All above | Decision rationale. |
| **11** | **Choose next roadmap.** Based on the outcome, select the next roadmap direction (see Section 11). | Outcome, rationale | Next roadmap: v2.14 Second Pilot / Source Expansion Planning, v2.14 Pilot Quality Improvements, or Core Discovery Pipeline Repair. |
| **12** | **Record dissent/uncertainty/open questions.** Document any factors that create uncertainty about the decision. Record any dissent (if multiple reviewers). List open questions that cannot be answered with Cycle 1 data. | Founder judgment | Dissent, uncertainty, and open questions recorded. |

### Procedure Rules

- Steps 1–2 are **gates**. If either fails, do not proceed. Escalate and document the failure.
- Steps must be completed in order. Do not skip steps.
- The decision is made in step 9, not before. Do not pre-judge the outcome before completing steps 3–8.
- If the founder cannot complete the procedure in one session, the state of completion must be recorded and resumed from the same step.

---

## 9. Decision Record Structure

The populated Go/No-Go decision record must contain the following fields. This framework defines the structure; the actual populated record is a runtime/output artifact.

### 9.1 Required Decision Record Fields

| # | Field | Type | Description |
|---|-------|------|-------------|
| 1 | `decision_id` | string | Unique identifier, format `gng_<YYYY-MM-DD>_<8char_hex>` |
| 2 | `pilot_run_id` | string | The `discovery_run_id` from `pilot_run_manifest.json` |
| 3 | `decided_at` | string | ISO 8601 UTC timestamp of when the decision was finalized |
| 4 | `founder` | string | Name or identifier of the founder making the decision |
| 5 | `outcome` | string | One of: `GO`, `CONDITIONAL_GO`, `NO_GO` |
| 6 | `summary` | string | One-paragraph plain-English summary of the decision and its basis |
| 7 | `quantitative_criteria_result` | object | Which quantitative criteria were met (see Section 9.2) |
| 8 | `qualitative_assessment` | object | Answers to QL-1 through QL-9 with brief explanations |
| 9 | `scoring_matrix` | object | Completed 10-dimension matrix with scores and total (see Section 7.4) |
| 10 | `top_opportunities` | array | List of top PROMOTE or NEEDS_MORE_EVIDENCE candidates with titles, scores, and validation readiness |
| 11 | `main_noise_findings` | string | Summary of the most important noise and quality findings |
| 12 | `source_quality_findings` | string | Summary of which sources/queries/repos were useful vs. noisy |
| 13 | `review_burden` | object | Review time, manageability assessment, friction summary |
| 14 | `traceability_status` | string | `clean`, `minor_issues`, or `broken` with details |
| 15 | `next_roadmap` | string | Explicit next roadmap direction (see Section 11) |
| 16 | `rationale` | string | Detailed rationale for the decision. Must cite specific pilot evidence. Must explain why the chosen outcome is correct and why the other outcomes were not chosen. |
| 17 | `risks` | array | Risks or uncertainties that could affect the decision's validity |
| 18 | `open_questions` | array | Questions that cannot be answered with Cycle 1 data alone |
| 19 | `explicit_non_approvals` | array | List of things NOT approved by this decision (see Section 12) |

### 9.2 Quantitative Criteria Result Structure

```yaml
quantitative_criteria_result:
  go_criteria:
    GQ-1_promote_candidates: {met: true|false, detail: "<text>"}
    GQ-2_validation_candidates: {met: true|false, detail: "<text>"}
    GQ-3_noise_rate_acceptable: {met: true|false, detail: "<text>"}
    GQ-4_traceability_clean: {met: true|false, detail: "<text>"}
    GQ-5_review_time_ok: {met: true|false, detail: "<text>"}
    GQ-6_match_rate_ok: {met: true|false, detail: "<text>"}
    GQ-7_useful_source_identified: {met: true|false, detail: "<text>"}
    GQ-8_source_quality_report_useful: {met: true|false, detail: "<text>"}
    GQ-9_specific_non_banal_cluster: {met: true|false, detail: "<text>"}
    met_count: <N>/9
  conditional_go_criteria:
    CQ-1_interesting_opportunity: {met: true|false, detail: "<text>"}
    CQ-2_noise_diagnosable: {met: true|false, detail: "<text>"}
    CQ-3_scoring_fixable: {met: true|false, detail: "<text>"}
    CQ-4_clusters_tunable: {met: true|false, detail: "<text>"}
    CQ-5_review_not_hopeless: {met: true|false, detail: "<text>"}
    CQ-6_tuning_actions_clear: {met: true|false, detail: "<text>"}
    CQ-7_traceability_acceptable: {met: true|false, detail: "<text>"}
    met_count: <N>/7
  no_go_criteria:
    NQ-1_zero_opportunities: {met: true|false, detail: "<text>"}
    NQ-2_overwhelming_noise: {met: true|false, detail: "<text>"}
    NQ-3_banal_clusters: {met: true|false, detail: "<text>"}
    NQ-4_abstract_candidates: {met: true|false, detail: "<text>"}
    NQ-5_trash_sorting_review: {met: true|false, detail: "<text>"}
    NQ-6_scoring_systematically_wrong: {met: true|false, detail: "<text>"}
    NQ-7_traceability_broken: {met: true|false, detail: "<text>"}
    NQ-8_source_quality_report_useless: {met: true|false, detail: "<text>"}
    met_count: <N>/8
```

### 9.3 Decision Record Template (Markdown)

```markdown
# Go / Conditional Go / No-Go Decision — Pilot Cycle 1

**Decision ID:** `gng_<YYYY-MM-DD>_<8char_hex>`
**Pilot Run ID:** `<run_id>`
**Decided At:** `<ISO 8601 UTC>`
**Founder:** `<name>`
**Framework Version:** `go_no_go_decision_framework.v1`

---

## Outcome

**`<GO | CONDITIONAL_GO | NO_GO>`**

---

## Summary

<one-paragraph summary>

---

## Quantitative Criteria Result

### GO Criteria

| # | Criterion | Met? | Detail |
|---|-----------|------|--------|
| GQ-1 | PROMOTE candidates (1–2) | `<yes/no>` | `<detail>` |
| GQ-2 | Validation-ready candidates (1+) | `<yes/no>` | `<detail>` |
| GQ-3 | Noise <60% or isolatable | `<yes/no>` | `<detail>` |
| GQ-4 | Traceability clean | `<yes/no>` | `<detail>` |
| GQ-5 | Review <120 min | `<yes/no>` | `<detail>` |
| GQ-6 | Match rate >=50% | `<yes/no>` | `<detail>` |
| GQ-7 | Useful source/query/repo | `<yes/no>` | `<detail>` |
| GQ-8 | Source Quality Report useful | `<yes/no>` | `<detail>` |
| GQ-9 | Specific non-banal cluster | `<yes/no>` | `<detail>` |
| **GO criteria met** | **`<N>`/9** | | |

### CONDITIONAL GO Criteria

| # | Criterion | Met? | Detail |
|---|-----------|------|--------|
| CQ-1 | Interesting opportunity exists | `<yes/no>` | `<detail>` |
| CQ-2 | Noise 60–80% but diagnosable | `<yes/no>` | `<detail>` |
| CQ-3 | Scoring fixable | `<yes/no>` | `<detail>` |
| CQ-4 | Clusters tunable | `<yes/no>` | `<detail>` |
| CQ-5 | Review not hopeless | `<yes/no>` | `<detail>` |
| CQ-6 | Tuning actions clear | `<yes/no>` | `<detail>` |
| CQ-7 | Traceability acceptable | `<yes/no>` | `<detail>` |
| **CONDITIONAL GO criteria met** | **`<N>`/7** | | |

### NO-GO Criteria

| # | Criterion | Met? | Detail |
|---|-----------|------|--------|
| NQ-1 | Zero validatable opportunities | `<yes/no>` | `<detail>` |
| NQ-2 | Noise >80% or undiagnosable | `<yes/no>` | `<detail>` |
| NQ-3 | Banal clusters | `<yes/no>` | `<detail>` |
| NQ-4 | Abstract candidates | `<yes/no>` | `<detail>` |
| NQ-5 | Review was trash sorting | `<yes/no>` | `<detail>` |
| NQ-6 | Scoring systematically wrong | `<yes/no>` | `<detail>` |
| NQ-7 | Traceability broken | `<yes/no>` | `<detail>` |
| NQ-8 | Source Quality Report useless | `<yes/no>` | `<detail>` |
| **NO-GO criteria met** | **`<N>`/8** | | |

---

## Qualitative Assessment

| # | Question | Answer | Notes |
|---|----------|--------|-------|
| QL-1 | Would I validate at least one idea? | `<yes/no>` | `<notes>` |
| QL-2 | Can I explain buyer + pain in one sentence? | `<yes/no>` | `<the sentence>` |
| QL-3 | Does evidence make pain feel real? | `<yes/no>` | `<notes>` |
| QL-4 | Plausible path to interviews? | `<yes/no>` | `<notes>` |
| QL-5 | Aligned with founder preferences? | `<yes/no>` | `<notes>` |
| QL-6 | Legally and ethically clean? | `<yes/no>` | `<notes>` |
| QL-7 | Saves time vs. manual browsing? | `<yes/no>` | `<notes>` |
| QL-8 | Surface something I might have missed? | `<yes/no>` | `<notes>` |
| QL-9 | Review package reduce cognitive load? | `<yes/no>` | `<notes>` |
| **Favorable answers** | **`<N>`/9** | | |

---

## Decision Scoring Matrix

| # | Dimension | Score (0/1/2) | Notes |
|---|-----------|---------------|-------|
| D1 | Opportunity quality | `<0/1/2>` | `<notes>` |
| D2 | Evidence traceability | `<0/1/2>` | `<notes>` |
| D3 | Business relevance | `<0/1/2>` | `<notes>` |
| D4 | Founder interest | `<0/1/2>` | `<notes>` |
| D5 | Review usability | `<0/1/2>` | `<notes>` |
| D6 | Noise manageability | `<0/1/2>` | `<notes>` |
| D7 | Source quality usefulness | `<0/1/2>` | `<notes>` |
| D8 | Scoring alignment | `<0/1/2>` | `<notes>` |
| D9 | Validation readiness | `<0/1/2>` | `<notes>` |
| D10 | Operational friction | `<0/1/2>` | `<notes>` |
| **TOTAL** | **`<N>`/20** | | |

**Matrix interpretation:** `<GO leaning / CONDITIONAL GO leaning / NO-GO leaning>`
**Matrix matches founder outcome?** `<yes/no>`
**If No, rationale:** `<rationale>`

---

## Top Opportunities

1. **`<title>`** (`<review_item_id>` / `<opportunity_id>`)
   - Founder decision: `<PROMOTE / NEEDS_MORE_EVIDENCE>`
   - Score: `<overall_score>`
   - Source diversity: `<N>`
   - Validation readiness: `<assessment>`
   - Rationale: `<why this is a top opportunity>`

2. **`<title>`** (`<review_item_id>` / `<opportunity_id>`)
   - ...

*(If none: "No opportunities met the validation threshold.")*

---

## Main Noise Findings

<summary of most important noise/quality findings from the Noise and Quality Analysis>

---

## Source Quality Findings

<summary of which sources/queries/repos were useful vs. noisy; which should be kept, capped, or killed>

---

## Review Burden

- **Review time:** `<N>` minutes
- **Manageable in target (120 min)?** `<yes/no>`
- **Friction points:** `<summary>`
- **Was review productive?** `<assessment>`

---

## Traceability Status

**Status:** `<clean / minor_issues / broken>`
**Details:** `<description of any issues found>`

---

## Next Roadmap

**Direction:** `<v2.14 Second Pilot / Source Expansion Planning / v2.14 Pilot Quality Improvements / Core Discovery Pipeline Repair>`

**Key activities:**
<list of key activities for the next roadmap>

---

## Rationale

<detailed rationale for the decision. Must cite specific pilot evidence. Must explain why the chosen outcome is correct and why the other outcomes were not chosen.>

---

## Risks

- `<risk 1>`
- `<risk 2>`
- ...

---

## Open Questions

- `<question 1>`
- `<question 2>`
- ...

---

## Explicit Non-Approvals

The following are **NOT** approved by this decision:

- `<non-approval 1>`
- `<non-approval 2>`
- ...

---

*Go/No-Go Decision — Pilot Cycle 1. Populated decision record. This is a runtime/output artifact. Do not commit unless explicitly approved (AG-5).*
```

---

## 10. Outcome-to-Next-Roadmap Mapping

### 10.1 GO → Next Roadmap

**Next roadmap options:**
- **v2.14 Second Operational Pilot Cycle** — Run a second pilot cycle to confirm findings before any source expansion.
- **v2.14 Cautious Source Expansion Planning** — Begin planning controlled source expansion, starting with Stack Exchange if a source gap is clear.

**Conditions:**
- Keep HN and GitHub Issues if they were useful.
- Consider Stack Exchange only if a clear source gap is identified (e.g., a pain domain under-represented in HN/GitHub).
- Do **not** add broad sources (Reddit, Discord, X/Twitter, Product Hunt, etc.) without a source-specific plan and explicit roadmap.
- Any new source added in v2.14+ requires its own query plan, allowlist (if applicable), and controlled smoke test before operational use.

**Do NOT:**
- Jump directly to broad source expansion.
- Add multiple sources simultaneously.
- Add sources without source-specific collection, filtering, and quality plans.

### 10.2 CONDITIONAL GO → Next Roadmap

**Next roadmap:** **v2.14 Pilot Quality Improvements**

**Focus areas:**
- **Noise filters** — Implement noise taxonomy categories (from item 9, Section 4) as heuristic filters.
- **HN query tuning** — Kill/cap/revise HN query buckets per source-level analysis recommendations.
- **GitHub repo allowlist tuning** — Remove low-signal repos; cap high-volume repos per repo-level analysis recommendations.
- **Scoring calibration** — Adjust scoring component rubrics per scoring calibration analysis recommendations.
- **PainCluster split/merge quality** — Improve near-duplicate detection; add over-merge checks; tune cluster assembly.
- **Founder review package clarity** — Improve review package structure, ordering, and evidence presentation based on founder friction notes.
- **Signal extraction improvement** — Tighten actor/workflow/object extraction requirements; improve pain explicitness detection.
- **Source quality report improvements** — Make recommendations more specific, actionable, and source-aware.

**After fixes:**
- Re-run pilot and re-evaluate using this same Go/No-Go decision framework.
- Do **not** proceed to source expansion until quality targets (noise <60%, match rate >=50%, review <120 min) are met.

### 10.3 NO-GO → Next Roadmap

**Next roadmap:** **Core Discovery Pipeline Repair**

**Focus areas:**
- **Signal extraction** — Revisit the candidate signal extractor heuristics. Possibly redesign extraction approach if fundamental problems are found.
- **Scoring model** — Revisit scoring formula weights and component definitions. If scoring systematically contradicts founder judgment, the formula may need structural changes, not just weight tuning.
- **PainCluster model** — Revisit cluster identity, deduplication, and cross-source consolidation logic. If >50% of clusters are generic or incorrectly merged/split, the clustering approach may need redesign.
- **Evidence schema** — Revisit how raw evidence is decomposed into actor/workflow/object/pain. If decomposition is poor, the rest of the pipeline cannot recover.
- **Founder review workflow** — Revisit the review package structure, decision recording format, and review burden. If review is fundamentally broken, the human-in-the-loop design may need rethinking.
- **Source strategy** — Reconsider whether HN + GitHub Issues are the right initial sources for the founder's ICP. If both sources are developer-heavy and the founder's ICP is SMB/finance/operations, the source selection itself may be the root cause.
- **ICP alignment** — Revisit whether the ICP profile is specific enough to drive useful filtering. If the profile is too broad or too narrow, the pipeline has no meaningful relevance target.

**After repairs:**
- Consider a narrower, more controlled test with manually curated evidence before another operational pilot.
- Do **not** expand sources until pipeline fundamentals are solid.
- When ready, run a new pilot cycle and re-evaluate.

---

## 11. Explicit Non-Approvals

Even a **GO** decision does **NOT** automatically approve any of the following. Each requires its own explicit roadmap item, founder approval, and (where applicable) controlled smoke test.

| # | Non-Approval | Description |
|---|-------------|-------------|
| NA-1 | **Product Hunt implementation** | Not approved. Requires separate v2.14+ roadmap item with source-specific plan. |
| NA-2 | **pimenov.ai implementation** | Not approved. Requires separate v2.14+ roadmap item with source-specific plan. |
| NA-3 | **Reddit integration** | Not approved. Requires separate v2.14+ roadmap item with API strategy, noise assessment, and moderation plan. |
| NA-4 | **Discord / Slack / X (Twitter) integration** | Not approved. Each requires separate roadmap items with API feasibility, ToS review, and collection strategy. |
| NA-5 | **AlternativeTo integration** | Not approved. Requires separate roadmap item with signal-type fit assessment. |
| NA-6 | **YC / Crunchbase integration** | Not approved. These are curated lists, not structured pain feeds. Requires signal-type fit assessment. |
| NA-7 | **App marketplaces / job boards / blogs / newsletters** | Not approved. Each requires ToS review, scraping risk assessment, and source-specific collection plan. |
| NA-8 | **Broad scraping** | Not approved. Collection must remain query-bounded and source-specific. |
| NA-9 | **Live source expansion without controlled smoke** | Not approved. Any new source must pass a controlled smoke test before operational use. |
| NA-10 | **Portfolio mutation** | Not approved. Portfolio state is not modified by this decision. |
| NA-11 | **Autonomous founder decisions** | Not approved. All promotion, killing, and validation decisions remain founder-made. |
| NA-12 | **Automated source expansion** | Not approved. Sources are added only through explicit roadmap items with founder approval. |
| NA-13 | **`KillReason` record creation** | Not approved. Kill rationale is recorded in founder review notes only. `KillReason` artifact creation belongs to a later explicitly approved workflow. |
| NA-14 | **Committing runtime pilot artifacts without AG-5** | Not approved. Runtime artifacts must not be committed unless explicitly approved. |

---

## 12. Edge Cases

The following edge cases are defined to handle ambiguous or borderline situations. If an edge case matches the pilot results, the specified handling should be applied.

| # | Edge Case | Handling |
|---|-----------|----------|
| EC-1 | **Strong technical pain but no identifiable buyer** | CONDITIONAL GO or PARK. Do not GO. The opportunity is not ready for validation. Record as NEEDS_MORE_EVIDENCE with a note to search for buyer evidence in the next cycle or in other sources. |
| EC-2 | **One excellent opportunity but high noise (>70%)** | CONDITIONAL GO, or GO with strict next-scope constraint: the single opportunity may be validated manually while pipeline quality fixes proceed. Do not ignore the noise problem. |
| EC-3 | **Good source quality (clear useful queries/repos) but no opportunities** | NO-GO or core pipeline repair. If sources produce clean evidence but the pipeline cannot find opportunities, the problem is in signal extraction, scoring, or ICP alignment, not in source selection. |
| EC-4 | **Broken traceability for some candidates** | NO-GO for affected candidates until fixed. If traceability is broken for reviewed candidates, those candidates are invalidated. If traceability is broken for non-reviewed candidates only, CONDITIONAL GO may be possible if the fix is clear and the reviewed candidates are clean. |
| EC-5 | **Founder likes an idea despite weak system score** | CONDITIONAL GO with a manual validation note. The system score is wrong — this is a scoring calibration issue to fix in v2.14. The idea may be valid; the founder should note what the system missed. |
| EC-6 | **System promotes but founder kills (pattern across multiple items)** | Scoring calibration issue. Record as a systematic over-promotion problem. If this is the dominant pattern, it pushes toward CONDITIONAL GO or NO-GO depending on severity and whether the scoring components at fault are identifiable. |
| EC-7 | **No PROMOTE items but several NEEDS_MORE_EVIDENCE with plausible pain** | CONDITIONAL GO. The pipeline is finding something but evidence is too thin. This suggests the source set is relevant but volume or query scope needs expansion within existing sources (not new sources). |
| EC-8 | **All PROMOTE items are from one source; the other source produced only noise** | CONDITIONAL GO. One source is useful; the noisy source needs tuning or removal. This is a source-level problem, not a pipeline-level problem. |
| EC-9 | **Review took >3 hours but founder found 1–2 useful opportunities** | CONDITIONAL GO. The pipeline produces signal but the review package needs significant improvement. Review package quality is a v2.14 fix priority. |
| EC-10 | **Evidence volume too low for any conclusion (dry cycle minimum not met)** | Do not force a GO or NO-GO. Record as CONDITIONAL GO with a note that evidence volume was insufficient. The next step is to increase input volume (more queries, broader allowlist, or live collection with founder approval) and re-run. |
| EC-11 | **Cross-source clusters are systematically weak or artificial** | CONDITIONAL GO. Cross-source consolidation is not working as intended. This is a clustering quality issue to fix in v2.14. Single-source clusters may still be useful. |
| EC-12 | **Founder review notes are incomplete or protocol was not followed** | Do not proceed to decision. The founder review must be completed per the Founder Review Protocol before the Go/No-Go decision can be made. Escalate and complete the review. |

---

## 13. Required Final Decision Statement

After the decision is made, the following summary must be recorded as the final decision statement:

```markdown
## Final Decision Statement — Pilot Cycle 1

**Outcome:** `<GO / CONDITIONAL GO / NO-GO>`

**Rationale:**
<paragraph explaining the decision>

**Top Evidence:**
- <evidence point 1>
- <evidence point 2>
- ...

**Top Opportunities:**
- <opportunity 1>
- <opportunity 2>
- ...
*(If none: "No opportunities met the validation threshold.")*

**Main Quality Concerns:**
- <concern 1>
- <concern 2>
- ...

**Next Roadmap:**
<explicit next roadmap direction>

**Explicitly Not Approved:**
- <non-approval 1>
- <non-approval 2>
- ...

**Open Questions:**
- <question 1>
- <question 2>
- ...
```

---

## 14. Decision Record Artifact Policy

| # | Rule |
|---|------|
| 1 | The **populated Go/No-Go decision record** is a **runtime/output artifact**. |
| 2 | It must be written to the same explicit `output_dir` as other pilot outputs. |
| 3 | It must **not** be committed to the repository unless explicitly approved by the founder (AG-5). |
| 4 | The recommended filename is `go_no_go_decision_v2_13.md` (as specified in the Pilot Cycle 1 Brief, Section 8, O-12). |
| 5 | An optional JSON companion (`go_no_go_decision_v2_13.json`) may follow the same structure for machine readability. |
| 6 | This **framework** document (`go_no_go_decision_framework_v2_13.md`) is a documentation artifact and may be committed as part of item 10. |

---

## 15. Do-Not-Do Rules

During the Go/No-Go decision process, the following are **forbidden**:

| # | Rule | Rationale |
|---|------|-----------|
| DND-1 | **Do not make the decision without completing the procedure (Section 8, steps 1–12).** | Skipping steps produces uninformed decisions. |
| DND-2 | **Do not make the decision without founder review notes.** | The founder's structured judgment is the most important input to the decision. |
| DND-3 | **Do not make the decision without noise and quality analysis.** | Understanding what went wrong is essential for choosing the right next roadmap. |
| DND-4 | **Do not treat the scoring matrix as a vote.** | The matrix is advisory. The founder may override it with documented rationale. |
| DND-5 | **Do not approve source expansion in a CONDITIONAL GO or NO-GO decision.** | Source expansion must not proceed until quality targets are met (CONDITIONAL GO) or the pipeline is repaired (NO-GO). |
| DND-6 | **Do not start v2.14 without an explicit roadmap.** | The next roadmap must be defined as a separate planning document. |
| DND-7 | **Do not mutate portfolio state.** | Portfolio is not modified by this decision. |
| DND-8 | **Do not create `KillReason` records.** | Kill rationale is recorded in founder review notes only. |
| DND-9 | **Do not lower the bar to force a GO decision.** | An honest NO-GO is more valuable than a forced GO based on lowered standards. |
| DND-10 | **Do not defer the decision.** | The decision must be made. "Undecided" is not an acceptable outcome. If evidence is ambiguous, choose the outcome that best matches the evidence and document the uncertainty. |

---

## 16. Definition of Done

Item 10 (Go / Conditional Go / No-Go Decision Framework) is complete when:

- [ ] **16.1** Go/No-Go Decision Framework exists at `docs/decisions/go_no_go_decision_framework_v2_13.md`.
- [ ] **16.2** Required inputs are listed (Section 2): 11 mandatory inputs + 5 reference documents.
- [ ] **16.3** Decision authority is explicit (Section 3): 8 authority rules.
- [ ] **16.4** Decision outcomes are defined (Section 4): GO, CONDITIONAL GO, NO-GO with definitions and next steps.
- [ ] **16.5** Quantitative criteria are defined (Section 5): GO (9 criteria), CONDITIONAL GO (7 criteria), NO-GO (8 criteria) with thresholds and decision rules.
- [ ] **16.6** Qualitative criteria are defined (Section 6): 9 founder questions with interpretation guidance.
- [ ] **16.7** Decision scoring matrix exists (Section 7): 10 dimensions with 0–2 scoring, interpretation, rules, and worksheet.
- [ ] **16.8** Decision meeting / review procedure exists (Section 8): 12 steps in order with gate enforcement.
- [ ] **16.9** Decision record structure exists (Section 9): 19 required fields, quantitative criteria result structure, and full Markdown template.
- [ ] **16.10** Outcome-to-next-roadmap mapping exists (Section 10): GO, CONDITIONAL GO, NO-GO mappings with focus areas and constraints.
- [ ] **16.11** Explicit non-approvals are listed (Section 11): 14 non-approvals with descriptions.
- [ ] **16.12** Edge cases are defined (Section 12): 12 edge cases with handling.
- [ ] **16.13** Required final decision statement template exists (Section 13).
- [ ] **16.14** Decision record artifact policy is defined (Section 14): 6 rules.
- [ ] **16.15** Do-not-do rules are defined (Section 15): 10 forbidden actions with rationales.
- [ ] **16.16** No pilot data is filled in — this is a framework/template only.
- [ ] **16.17** No actual Go/No-Go decision is made.
- [ ] **16.18** No founder decisions, `KillReason` records, or portfolio mutations are created.
- [ ] **16.19** No source expansion is approved.
- [ ] **16.20** `.\scripts\dev-git-check.ps1` passes.
- [ ] **16.21** `git status --short` shows only allowed files before commit.
- [ ] **16.22** Roadmap item 10 marked complete in `docs/roadmaps/OOS_roadmap_v2_13_operational_pilot_go_no_go_checklist.md`.
- [ ] **16.23** One local commit exists with message: `[v2.13] 10 define go no-go decision framework`.

---

## 17. References

- [Founder ICP Preference Profile v2.13](founder_icp_preference_profile_v2_13.md) — ICP definitions, excluded markets, relevance signals, noise definitions, review rubric
- [Pilot Cycle 1 Brief v2.13](pilot_cycle_1_brief_v2_13.md) — success/failure criteria, timebox, decision outcomes, evidence volume targets
- [Founder Review Protocol v2.13](founder_review_protocol_v2_13.md) — decision definitions, scoring rubric, alignment check, review burden assessment
- [Pilot Results Report Template v2.13](pilot_results_report_template_v2_13.md) — report structure, metrics definitions, criteria check format
- [Noise and Quality Analysis Framework v2.13](noise_quality_analysis_framework_v2_13.md) — noise taxonomy, quality thresholds, source/cluster/scoring analysis, tuning actions
- [PainCluster Contract](../contracts/pain_cluster_contract.md) — cluster schema, scoring formula, promotion rules
- [Operational Discovery Pilot Run Contract](../contracts/operational_discovery_pilot_run_contract.md) — pilot run lifecycle, founder review loop, Go/No-Go criteria
- [OOS Roadmap v2.13 Checklist](../roadmaps/OOS_roadmap_v2_13_operational_pilot_go_no_go_checklist.md) — parent roadmap

---

## 18. Self-Audit Checklist

- [x] **Title and status present** (header): Title, status, roadmap item, branch, based-on references
- [x] **Purpose stated** (Section 1): What this framework is and is not; the 5 questions it answers
- [x] **Required inputs listed** (Section 2): 11 mandatory inputs + 5 reference documents
- [x] **Decision authority explicit** (Section 3): 8 authority rules (DA-1 through DA-8)
- [x] **Decision outcomes defined** (Section 4): GO, CONDITIONAL GO, NO-GO with definitions, next steps, and what each does and does not mean
- [x] **Quantitative criteria defined** (Section 5): GO (9 criteria GQ-1 through GQ-9), CONDITIONAL GO (7 criteria CQ-1 through CQ-7), NO-GO (8 criteria NQ-1 through NQ-8)
- [x] **Qualitative criteria defined** (Section 6): 9 founder questions (QL-1 through QL-9) with interpretation
- [x] **Decision scoring matrix exists** (Section 7): 10 dimensions (D1–D10) with 0–2 scoring, interpretation bands, rules, worksheet
- [x] **Decision procedure defined** (Section 8): 12 steps in order with gate enforcement
- [x] **Decision record structure exists** (Section 9): 19 fields, criteria result structure, full Markdown template
- [x] **Outcome-to-next-roadmap mapping exists** (Section 10): GO, CONDITIONAL GO, NO-GO mappings with focus areas
- [x] **Explicit non-approvals listed** (Section 11): 14 non-approvals
- [x] **Edge cases defined** (Section 12): 12 edge cases with handling
- [x] **Final decision statement template exists** (Section 13)
- [x] **Artifact policy defined** (Section 14): 6 rules
- [x] **Do-not-do rules defined** (Section 15): 10 forbidden actions
- [x] **Definition of Done present** (Section 16): 23 completion criteria
- [x] **References present** (Section 17): 8 referenced documents
- [x] **No pilot data filled in** — this is a framework/template only
- [x] **No actual Go/No-Go decision made**
- [x] **No founder decisions, KillReason records, or portfolio mutations created**
- [x] **No source expansion approved**
- [x] **No source code, test, script, or artifact modifications**

---

*Go / Conditional Go / No-Go Decision Framework v2.13. Operational decision framework only. Defines the decision process, required evidence, thresholds, record structure, and next-roadmap mapping. Does not make the actual Go/No-Go decision. Does not create founder decisions, KillReason records, or portfolio mutations. Does not modify source code, tests, scripts, or pipeline behavior.*
