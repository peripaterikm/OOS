# OOS v2.13 — Pilot Run Procedure

**Title:** OOS v2.13 — Pilot Run Procedure
**Status:** Draft / operational run procedure
**Roadmap item:** v2.13 item 6
**Branch:** `ops/v2-13-operational-pilot-cycle-1`
**Created:** 2026-05-13
**Based on:**
- [Founder ICP Preference Profile v2.13](founder_icp_preference_profile_v2_13.md)
- [Pilot Cycle 1 Brief v2.13](pilot_cycle_1_brief_v2_13.md)
- [HN Pilot Query Plan v2.13](hacker_news_pilot_query_plan_v2_13.md)
- [GitHub Issues Repo Allowlist and Query Plan v2.13](github_issues_repo_allowlist_query_plan_v2_13.md)
- [Pilot Input Preparation Procedure v2.13](pilot_input_preparation_procedure_v2_13.md)
- [Operational Discovery Pilot Run Contract](../contracts/operational_discovery_pilot_run_contract.md)

---

## 1. Purpose

The purpose of this procedure is to define how to run the v2.13 Operational Discovery Pilot on bounded HN + GitHub Issues inputs and verify that the generated outputs are complete, traceable, source-scoped, and ready for founder review.

This is **not**:
- live collection;
- source expansion;
- production deployment;
- automated founder decision-making;
- portfolio mutation;
- KillReason creation.

This **is**:
- a controlled operational pilot run procedure;
- a structured execution and verification guide;
- a pre-review gate that ensures outputs are valid before the founder sees them.

This procedure does **not** authorize running the pilot. The pilot may only be run when bounded inputs and an explicit `output_dir` exist, and when all preconditions in Section 3 are satisfied.

This procedure does **not** authorize committing runtime artifacts. Committing generated pilot outputs requires explicit founder approval (AG-5).

---

## 2. Preconditions

Before running the pilot, the following must be confirmed:

| # | Precondition | Status |
|---|-------------|--------|
| P-1 | Founder ICP profile exists at [`founder_icp_preference_profile_v2_13.md`](founder_icp_preference_profile_v2_13.md) | Required |
| P-2 | Pilot Cycle 1 brief exists at [`pilot_cycle_1_brief_v2_13.md`](pilot_cycle_1_brief_v2_13.md) | Required |
| P-3 | HN query plan exists at [`hacker_news_pilot_query_plan_v2_13.md`](hacker_news_pilot_query_plan_v2_13.md) | Required |
| P-4 | GitHub Issues repo allowlist/query plan exists at [`github_issues_repo_allowlist_query_plan_v2_13.md`](github_issues_repo_allowlist_query_plan_v2_13.md) | Required |
| P-5 | Pilot input preparation procedure exists at [`pilot_input_preparation_procedure_v2_13.md`](pilot_input_preparation_procedure_v2_13.md) | Required |
| P-6 | Input package prepared per the input preparation procedure (Section 12 of that document) | Required |
| P-7 | Source scope check passed (only `hacker_news` and `github_issues` present; no deferred sources) | Required |
| P-8 | Traceability check passed (zero missing URLs, zero placeholder URLs, zero API URLs as `source_url`) | Required |
| P-9 | `output_dir` explicitly selected and recorded | Required |
| P-10 | Founder review time reserved (48 hours, max 2 hours active review) | Required |
| P-11 | Live collection approvals recorded if live collection was used (AG-1 for HN, AG-2 for GitHub) | Required if Mode C |
| P-12 | GitHub repo allowlist approved if live GitHub was used (AG-3) | Required if Mode C for GitHub |
| P-13 | Runtime artifact commit approval recorded if generated files will be committed (AG-5) | Required before commit |

**All preconditions P-1 through P-10 must be confirmed before the pilot run begins.** Preconditions P-11 through P-13 are conditional on the chosen run mode and post-run actions.

---

## 3. Allowed Run Modes

Three run modes are defined. The mode must be explicitly chosen before the pilot run begins.

### 3.1 Mode A — Dry / Manual Bounded Run

The pilot runs on manually prepared bounded input. No live APIs are called during the run.

| Attribute | Value |
|-----------|-------|
| **Input source** | Manual bounded input (Mode A from input preparation procedure) |
| **Live API calls during run** | No |
| **Deterministic** | Yes — same input produces same output |
| **Repeatable** | Yes — re-run produces identical artifacts |
| **Recommended for** | First dry cycle when live access is not approved |
| **Volume** | Dry-cycle minimums apply (see Section 15) |

### 3.2 Mode B — Prepared JSON Fixture Run

The pilot runs on prepared JSON fixture input. No live APIs are called during the run.

| Attribute | Value |
|-----------|-------|
| **Input source** | Fixture/prepared JSON input (Mode B from input preparation procedure) |
| **Live API calls during run** | No |
| **Deterministic** | Yes — fixture input produces identical output every run |
| **Repeatable** | Yes — suitable for pipeline validation and regression testing |
| **Recommended for** | Deterministic local input; repeatable validation |
| **Volume** | Dry-cycle minimums or operational targets as prepared |

### 3.3 Mode C — Live-Approved Bounded Run

The pilot runs on live-collected input. **Only allowed if explicit founder approvals for live HN (AG-1) and/or live GitHub (AG-2) exist.**

| Attribute | Value |
|-----------|-------|
| **Input source** | Live opt-in collection (Mode C from input preparation procedure) |
| **Live API calls during run** | The *input collection* phase used live APIs; the *pilot run* itself processes pre-collected input |
| **Caps** | Must use collection caps from the HN and GitHub query plans |
| **Query plans** | Must use the approved HN Pilot Query Plan and/or GitHub Issues Repo Allowlist and Query Plan |
| **Output policy** | Must write runtime outputs only to explicit `output_dir` |
| **Repository artifacts** | No default writes to `artifacts/` or any repository path |

### 3.4 Mode Selection Table

| Scenario | Recommended Mode |
|----------|-----------------|
| Live HN + live GitHub not approved | **Mode A** or **Mode B** |
| Live HN approved, live GitHub not approved | Process HN input (pre-collected) + Mode A/B for GitHub |
| Live GitHub approved, live HN not approved | Mode A/B for HN + process GitHub input (pre-collected) |
| Both live sources approved | Process pre-collected input from both |

**Note:** The pilot run procedure itself does not perform live collection. Live collection is an input preparation concern (see the input preparation procedure). The pilot run operates on bounded input that has already been collected and validated.

---

## 4. Run Input Package

The following files must be present and validated before the pilot run begins. These are runtime/pre-run files and should not be committed unless explicitly approved (AG-5).

| # | File | Format | Description | Required? |
|---|------|--------|-------------|-----------|
| 1 | `raw_evidence.json` (or per-source equivalents) | JSON | Bounded input evidence records with `source_id`, `source_type`, `source_url` | **Yes** |
| 2 | `input_manifest.json` or `input_manifest.md` | JSON or Markdown | Manifest describing input package contents, mode, counts, approvals, limitations | **Yes** |
| 3 | `source_scope_check.json` or `source_scope_check.md` | JSON or Markdown | Results of source scope validation (V-1 through V-7 from input preparation procedure) | **Yes** |
| 4 | `traceability_check.json` or `traceability_check.md` | JSON or Markdown | Results of traceability validation (V-8 through V-17 from input preparation procedure) | **Yes** |
| 5 | `approval_record.json` or `approval_record.md` | JSON or Markdown | Record of all approvals granted for this pilot input | **Yes** |
| 6 | `notes_on_manual_selection.md` | Markdown | Notes explaining manual selection decisions | Only if Mode A |

### 4.1 Input Package Validation

Before running the pilot, confirm:
- All required files exist and are non-empty.
- `source_scope_check` confirms only `hacker_news` and `github_issues` present (or Stack Exchange if stretch-approved).
- `traceability_check` confirms zero missing URLs, zero placeholder URLs, zero API URLs as `source_url`.
- `approval_record` confirms all required approvals are recorded (live HN if used, live GitHub if used, repo allowlist if GitHub present).
- `input_manifest` describes the input: mode, counts, queries/repos used, known limitations.

---

## 5. Execution Path

The pilot is executed using the existing v2.12 operational discovery pilot API.

### 5.1 Entry Point

The intended entry point is:

- **Module:** `src/oos/operational_discovery_pilot.py`
- **Function:** `run_operational_discovery_pilot()`

This procedure does **not** modify the code, CLI, or API. It references the existing function signature for descriptive purposes only.

### 5.2 Execution Parameters

The pilot run must be configured with these explicit parameters:

| Parameter | Value | Notes |
|-----------|-------|-------|
| `raw_evidence` | Bounded raw evidence input (from input package) | Loaded from the prepared input |
| `candidate_signals` | `None` or pre-prepared candidate signals | Optional; if `None`, the pilot extracts signals from raw evidence |
| `opportunity_candidates` | `None` or pre-prepared opportunity candidates | Optional; if `None`, the pilot generates candidates from clusters |
| `discovery_run_id` | Explicit string, e.g. `"pilot_run_2026-05-13_a1b2c3d4"` | Must be unique; format: `pilot_run_YYYY-MM-DD_<8char_hex>` |
| `created_at` | ISO 8601 UTC timestamp | Explicit, not auto-generated; e.g. `"2026-05-13T12:00:00Z"` |
| `output_dir` | Explicit directory path | Must be provided by the caller; no default writes |
| `stretch_allowed` | `False` | Must be `False` unless Stack Exchange stretch is explicitly approved (AG-4) |

### 5.3 Execution Steps

1. **Load bounded raw evidence input** from the input package.
2. **Optionally load `candidate_signals`** if pre-prepared; otherwise the pilot extracts them.
3. **Optionally load `opportunity_candidates`** if pre-prepared; otherwise the pilot generates them.
4. **Set explicit `discovery_run_id`** — a unique, traceable identifier.
5. **Set explicit `created_at`** — a fixed ISO 8601 UTC timestamp.
6. **Pass explicit `output_dir`** — the directory where all pilot outputs will be written.
7. **Set `stretch_allowed=False`** unless Stack Exchange is explicitly approved (AG-4). If stretch is approved, set `stretch_allowed=True` and document in run notes.
8. **Run the pilot** — call `run_operational_discovery_pilot()` with the configured parameters.
9. **Capture the result** — the function returns a result object with `is_valid`, `validation_summary`, and paths to all generated artifacts.

### 5.4 What This Procedure Does NOT Require

- A new CLI command — the existing function is sufficient.
- A new CLI wrapper — manual invocation or script-based invocation is acceptable.
- Live APIs during the pilot run — the pilot operates on pre-collected input.
- LLM/API calls in validation — all validation is structural and deterministic.

---

## 6. Required Output Artifacts

After the pilot run completes, verify that the `output_dir` run folder contains the following artifacts:

### 6.1 Mandatory Artifacts

| # | Artifact | Format | Description |
|---|----------|--------|-------------|
| 1 | `raw_evidence.json` | JSON | Validated raw evidence records used as input |
| 2 | `candidate_signals.json` | JSON | Extracted candidate signals with scores and source traceability |
| 3 | `pain_clusters.json` | JSON | Synthesized pain clusters with member signals and scores |
| 4 | `source_quality_report.json` | JSON | Machine-readable quality metrics per source/query/repo |
| 5 | `source_quality_report.md` | Markdown | Human-readable quality summary with recommendations |
| 6 | `founder_review_package.json` | JSON | Structured package for founder review: top clusters, candidates, traceability |
| 7 | `founder_review_package.md` | Markdown | Human-readable review package |
| 8 | `validation_summary.json` | JSON | Pipeline validation: format checks, traceability pass/fail, source scope compliance |
| 9 | `pilot_run_manifest.json` | JSON | Timestamp, parameters, sources used, evidence counts, pipeline version |

### 6.2 Optional Artifacts

| # | Artifact | Format | Description |
|---|----------|--------|-------------|
| 10 | `opportunity_candidates.json` | JSON | Opportunity candidates framed from top-scoring pain clusters |
| 11 | `duplicates.json` | JSON | Records of detected and merged duplicate evidence items |

### 6.3 Artifact Verification

For each mandatory artifact, confirm:
- **Existence** — the file exists and is non-empty.
- **Format** — valid JSON (for `.json` files) or valid Markdown (for `.md` files).
- **Content** — contains expected top-level fields (see artifact-specific verification in Sections 9–11).

---

## 7. Artifact Policy

### 7.1 Core Rules

| # | Rule |
|---|------|
| 1 | `output_dir` must be **explicit** — the caller provides the destination directory. |
| 2 | **No default writes** to repository `artifacts/` or any repository path. |
| 3 | Generated runtime files **remain uncommitted** unless AG-5 explicitly approves committing them. |
| 4 | If committed, runtime artifacts must be treated as **evidence/sample artifacts** and documented as such. |
| 5 | **Final dev ledger reports** are separate from runtime pilot outputs. |
| 6 | The `output_dir` must be recorded in `pilot_run_manifest.json` and in the pilot run notes. |

### 7.2 Acceptable `output_dir` Conventions

| Convention | Example | Committed? |
|------------|---------|------------|
| External directory outside repo | `C:\pilot_outputs\cycle_1\` | No |
| Temp directory | `%TEMP%\oos_pilot_cycle_1\` | No |
| Repository path with explicit approval | `artifacts\discovery\pilot_runs\cycle_1\` | Only if AG-5 approved |

### 7.3 What Must NOT Happen

- The pilot orchestrator must not write to `artifacts/` unless the caller explicitly provides it as `output_dir`.
- No default writes to any repository path.
- No writes to `docs/`, `src/`, `tests/`, `scripts/`, `config/`, or `examples/` as pilot runtime outputs.

---

## 8. Post-Run Validation Checks

After the pilot run completes, verify **all** of the following checks. If any check fails, do not proceed to founder review.

### 8.1 Core Validity

- [ ] **V-1** `result.is_valid` is `true`.
- [ ] **V-2** `validation_summary.json` exists and is non-empty.

### 8.2 Volume Checks

- [ ] **V-3** `raw_evidence_count` is within approved range (see Section 15 for dry run, Section 16 for operational run).
- [ ] **V-4** `candidate_signal_count > 0` OR documented reason why zero signals were produced.
- [ ] **V-5** `pain_cluster_count > 0` OR documented reason why zero clusters were formed.

### 8.3 Artifact Existence

- [ ] **V-6** `source_quality_report.json` and `source_quality_report.md` exist.
- [ ] **V-7** `founder_review_package.json` and `founder_review_package.md` exist.

### 8.4 Traceability

- [ ] **V-8** Source URL traceability is clean — zero missing `source_url` fields.
- [ ] **V-9** No deferred sources present — only `hacker_news` and `github_issues` appear.
- [ ] **V-10** No unknown `source_id` values present.
- [ ] **V-11** No unknown `source_type` values present.
- [ ] **V-12** No `urn:` URLs anywhere in output artifacts.
- [ ] **V-13** No `github://` URLs anywhere in output artifacts.
- [ ] **V-14** No missing `source_url` on any evidence record, candidate signal, or cluster reference.

### 8.5 Source Scope

- [ ] **V-15** Only `hacker_news` and `github_issues` source types appear, unless Stack Exchange stretch was approved.
- [ ] **V-16** No Product Hunt / pimenov.ai / Reddit / social / other deferred sources.
- [ ] **V-17** No `source_url` pointing to `producthunt.com`, `reddit.com`, `twitter.com`, `x.com`, `discord.com`, or other deferred source domains.

### 8.6 Output Integrity

- [ ] **V-18** All output paths stay under the explicit `output_dir`.
- [ ] **V-19** No output file was written to a repository path that was not provided as `output_dir`.
- [ ] **V-20** `discovery_run_id` in `pilot_run_manifest.json` matches the explicit run ID provided.
- [ ] **V-21** `created_at` in `pilot_run_manifest.json` matches the explicit timestamp provided.

### 8.7 Validation Outcome

- **All V-1 through V-21 pass** → pilot run outputs are valid; proceed to founder review handoff.
- **Any V-1 through V-21 fail** → block founder review; classify failure per Section 11; fix and re-run.

---

## 9. Source Quality Report Verification

Verify the Source Quality Report (both JSON and Markdown) satisfies the following checks:

### 9.1 Structural Checks

- [ ] **SQ-1** `source_metrics` in the JSON report includes entries for `hacker_news` and/or `github_issues`.
- [ ] **SQ-2** No deferred source metrics are present (no `product_hunt`, `reddit`, etc.).
- [ ] **SQ-3** `accepted_count`, `weak_count`, `noise_count` are present and are non-negative integers.
- [ ] **SQ-4** Noise categories are present (list of `{category, count, source}`).

### 9.2 Content Checks

- [ ] **SQ-5** `traceability_summary` is present with `total_source_urls`, `missing_url_count`, `placeholder_url_count`, `source_url_validation_passed`.
- [ ] **SQ-6** Per-source metrics include `signal_rate`, `noise_rate`, `missing_url_count`, `placeholder_url_count`.
- [ ] **SQ-7** Per-source `source_url_validation_passed` is `true` for each source.

### 9.3 Usefulness Checks

- [ ] **SQ-8** Top pain clusters are reflected in the report (if any clusters exist).
- [ ] **SQ-9** The report provides source-level quality information that helps decide which queries/repos to tune or retire for Cycle 2.
- [ ] **SQ-10** The Markdown report is human-readable and actionable.

### 9.4 Source Quality Report Failure

If the Source Quality Report fails any of SQ-1 through SQ-10:
- Classify as `source_quality_report_failure`.
- Do not proceed to founder review.
- Document the failure reason.
- Fix the pipeline or input and re-run.

---

## 10. Founder Review Package Verification

Verify the Founder Review Package (both JSON and Markdown) satisfies the following checks:

### 10.1 Structural Checks

- [ ] **FR-1** Package exists in both JSON and Markdown formats.
- [ ] **FR-2** `traceability_status` is `clean` (not `broken`, not `partial`).
- [ ] **FR-3** Every review item has evidence links (at least one `source_url` per item).
- [ ] **FR-4** Ranked clusters are present with scores, recurrence, and source diversity.

### 10.2 Content Checks

- [ ] **FR-5** Recommended decisions are **advisory only** — marked as `founder_review_recommendation`, not as final decisions.
- [ ] **FR-6** No `founder_final_decision` field is populated at this stage.
- [ ] **FR-7** No founder decisions have been ingested.
- [ ] **FR-8** No `KillReason` records have been created.
- [ ] **FR-9** No portfolio mutation has occurred.
- [ ] **FR-10** Review items are manageable in number (not overwhelming; see Section 16 for operational targets).

### 10.3 Founder Review Package Failure

If the Founder Review Package fails any of FR-1 through FR-10:
- Classify as `founder_review_package_failure`.
- Do not proceed to founder review.
- Document the failure reason.
- Fix the pipeline or input and re-run.

---

## 11. Failure Handling

If the pilot run fails at any stage, follow these rules.

### 11.1 General Rules

| # | Rule |
|---|------|
| 1 | **Do not proceed to founder review** until all failures are resolved. |
| 2 | **Record the failure reason** in pilot run notes. |
| 3 | **Classify the failure** using one of the categories below. |
| 4 | **Do not silently drop malformed evidence.** Records that fail validation must be documented. |
| 5 | **Do not patch `source_url` with a placeholder.** Missing URLs must cause rejection, not fabrication. |
| 6 | **Do not expand sources to compensate** for insufficient evidence. Reduce scope or fix input instead. |
| 7 | **Do not edit `source_id` or `source_type`** to bypass source scope gates. |

### 11.2 Failure Classification

| Failure Class | Description | Action |
|---------------|-------------|--------|
| `input_validation_failure` | Raw evidence input failed validation (missing fields, malformed records) | Fix input; re-validate per input preparation procedure Section 6; re-run |
| `source_scope_failure` | Deferred sources or unknown `source_id`/`source_type` detected in input or output | Remove violating records; document removal; re-validate; re-run |
| `traceability_failure` | Missing `source_url`, placeholder URLs, or API URLs as `source_url` detected | Correct or remove affected records; re-validate traceability; re-run |
| `artifact_write_failure` | Pilot failed to write required output artifacts to `output_dir` | Check disk space, permissions, path validity; fix; re-run |
| `clustering_failure` | Pain clusters could not be formed or are empty | Document reason; check input quality and signal sufficiency; may require input scope adjustment |
| `source_quality_report_failure` | Source Quality Report is missing, incomplete, or invalid | Diagnose which metrics or sections failed; fix pipeline or input; re-run |
| `founder_review_package_failure` | Founder Review Package is missing, incomplete, or has broken traceability | Diagnose missing items; fix pipeline or input; re-run |
| `validation_summary_failure` | `validation_summary.json` is missing or `is_valid` is `false` | Inspect validation errors; fix root cause; re-run |

### 11.3 Post-Failure Procedure

1. Identify failure class.
2. Record failure in pilot run notes: timestamp, failure class, specific error, input state.
3. Fix the root cause (repair input, adjust scope, correct configuration).
4. Re-run full validation (Section 8).
5. Do not proceed to founder review until all validation checks pass.
6. Document any evidence records removed or modified during repair.

---

## 12. Operational Run Notes

After the pilot run completes successfully, capture the following operational run notes. These notes should be recorded in the pilot run manifest or a separate run notes file within `output_dir`.

| # | Field | Description |
|---|-------|-------------|
| 1 | `run_id` | The explicit `discovery_run_id` used, e.g. `"pilot_run_2026-05-13_a1b2c3d4"` |
| 2 | `created_at` | The explicit ISO 8601 UTC timestamp used |
| 3 | `input_mode` | Which run mode was used: `Mode A — Dry/Manual`, `Mode B — Fixture`, or `Mode C — Live-Approved` |
| 4 | `output_dir` | The explicit output directory path |
| 5 | `source_counts` | Per-source evidence counts: `hacker_news: N`, `github_issues: M` |
| 6 | `approvals_used` | Which approval gates were recorded: AG-1 (live HN), AG-2 (live GitHub), AG-3 (repo allowlist), AG-4 (Stack Exchange stretch) |
| 7 | `hn_query_buckets_used` | Which HN query buckets (A–G) contributed evidence, and how many items per bucket |
| 8 | `github_repos_used` | Which GitHub repos from the allowlist contributed evidence, and how many items per repo |
| 9 | `caps_applied` | Which caps were enforced: per-source cap, per-repo cap, per-query cap, anti-dominance rules |
| 10 | `deviations_from_plan` | Any deviations from the HN query plan, GitHub query plan, or input preparation procedure |
| 11 | `known_limitations` | Known limitations of this run: underrepresented themes, source bias, dry-cycle volume, missing sources |
| 12 | `next_step` | The immediate next step: `"handoff to founder review"` |

---

## 13. Handoff to Founder Review

After the pilot run completes successfully and all validation checks pass, hand off the following artifacts to the founder.

### 13.1 Handoff Package

| # | Artifact | Format | Purpose |
|---|----------|--------|---------|
| 1 | `founder_review_package.md` | Markdown | Primary review document: ranked clusters, opportunity candidates, evidence links, advisory recommendations |
| 2 | `founder_review_package.json` | JSON | Structured version of the review package |
| 3 | `source_quality_report.md` | Markdown | Human-readable quality summary: which sources/queries worked, which produced noise |
| 4 | `source_quality_report.json` | JSON | Machine-readable quality metrics |
| 5 | `validation_summary.json` | JSON | Confirmation that all validation checks passed |
| 6 | `pilot_run_manifest.json` | JSON | Run metadata: parameters, counts, approvals, limitations |

### 13.2 Handoff Rules

| # | Rule |
|---|------|
| 1 | **Schedule review within 48 hours** of handoff. |
| 2 | **Do not treat recommendations as final decisions.** The founder review package contains advisory recommendations only. |
| 3 | **Founder review protocol (item 7) governs decisions.** The handoff provides input to the founder review; the review protocol defines how decisions are made and recorded. |
| 4 | **Do not pre-populate founder decisions.** No `founder_final_decision`, `KillReason`, or portfolio mutation may exist at handoff time. |
| 5 | **Remind the founder of the timebox:** maximum 2 hours active review time. |
| 6 | **Provide context:** include the Pilot Cycle 1 Brief and Founder ICP Preference Profile as reference documents for the review. |

### 13.3 Handoff Checklist

Before delivering the handoff package:

- [ ] **H-1** All validation checks (Section 8, V-1 through V-21) pass.
- [ ] **H-2** Source Quality Report is verified (Section 9, SQ-1 through SQ-10).
- [ ] **H-3** Founder Review Package is verified (Section 10, FR-1 through FR-10).
- [ ] **H-4** `validation_summary.is_valid` is `true`.
- [ ] **H-5** Traceability is clean — zero missing, placeholder, or malformed URLs.
- [ ] **H-6** Source scope is valid — only `hacker_news` and `github_issues` (or stretch-approved Stack Exchange).
- [ ] **H-7** Founder has confirmed review availability (48 hours, max 2 hours).
- [ ] **H-8** Operational run notes are complete (Section 12, all 12 fields).

---

## 14. Dry-Run Minimum Acceptance

For a first dry/manual run (Mode A or Mode B), the following minimums apply. These are lower than operational targets to allow for small, controlled first runs.

### 14.1 Dry-Run Minimum Targets

| Metric | Minimum | Notes |
|--------|---------|-------|
| Raw evidence items | **10** | At least 10 items preferred; if fewer, document why |
| Sources represented | **1** | At least one source represented; ideally both HN and GitHub |
| Candidate signals | **3** | Or documented reason why fewer |
| Pain clusters | **1** | At least one PainCluster or documented reason why none emerged |
| Opportunity candidates | **0** | Not required for dry run; zero is acceptable with documented reason |

### 14.2 Dry-Run Acceptance Rules

- A dry run producing fewer than 10 raw evidence items is **not automatically a failure** — but requires a documented explanation of why so few items were collected.
- A dry run that produces zero candidate signals or zero pain clusters **requires a documented explanation**.
- A dry run that produces zero opportunity candidates is **not a failure** — but requires a documented explanation (e.g., evidence too thin, thematic mismatches, excessive noise).
- **Traceability must be clean regardless of volume.** Zero missing URLs, zero placeholder URLs.
- **Source scope must be valid regardless of volume.** No deferred sources.

### 14.3 Dry-Run Ideal

| Metric | Ideal |
|--------|-------|
| Raw evidence items | 10–25 |
| Sources represented | 2 (HN + GitHub) |
| Candidate signals | 3–10 |
| Pain clusters | 2–4 (including cross-source where possible) |
| Opportunity candidates | 1 (or documented reason) |

---

## 15. Full Operational Run Acceptance

For an intended operational run (Mode C or comprehensive Mode B), the following targets apply as defined in the Pilot Cycle 1 Brief.

### 15.1 Operational Run Targets

| Metric | Target | Source |
|--------|--------|--------|
| Raw evidence items | 50–150 | Pilot Cycle 1 Brief, Section 4 |
| Candidate signals | 10–30 | Pilot Cycle 1 Brief, Section 4 |
| Pain clusters | 3–7 | Pilot Cycle 1 Brief, Section 4 |
| Opportunity candidates | 3–5 | Pilot Cycle 1 Brief, Section 4 |
| Ideas worth real validation | 1–2 | Pilot Cycle 1 Brief, Section 4 |

### 15.2 Operational Run Quality Gates

| Metric | Threshold |
|--------|-----------|
| Source Quality Report | Useful — identifies which sources/queries/repos to tune |
| Founder Review Package | Manageable — not overwhelming; founder can complete review within 2 hours |
| Traceability | Clean — zero missing, placeholder, or malformed URLs |
| Source scope | Valid — only `hacker_news` and `github_issues` (or stretch-approved Stack Exchange) |
| Cross-source clusters | At least 2 clusters with `source_diversity >= 2` (ideal; not a hard gate for first cycle) |

---

## 16. Do Not Proceed Rules

Do **not** proceed to founder review if any of the following conditions are true:

| # | Condition | Rationale |
|---|-----------|-----------|
| DNP-1 | Traceability is broken (missing URLs, placeholder URLs, API URLs as `source_url`) | Founder cannot verify evidence origin |
| DNP-2 | Deferred sources are present in outputs | Source scope violation |
| DNP-3 | Source scope is invalid (unknown `source_id` or `source_type`) | Cannot trust evidence provenance |
| DNP-4 | `output_dir` is missing or empty | No outputs to review |
| DNP-5 | `validation_summary.json` is missing or `is_valid` is `false` | Pipeline validation failed |
| DNP-6 | `founder_review_package.json` or `founder_review_package.md` is missing | Founder has nothing to review |
| DNP-7 | `source_quality_report.json` or `source_quality_report.md` is missing | Cannot assess evidence quality |

**If any DNP condition is true, classify the failure per Section 11, fix the root cause, and re-run the pilot.**

---

## 17. Self-Audit Checklist

- [ ] **Title and status present** (header): Title, status, roadmap item, branch, based-on references
- [ ] **Purpose stated** (Section 1): What this procedure is and is not
- [ ] **Preconditions defined** (Section 2): 13 preconditions with status indicators
- [ ] **Run modes defined** (Section 3): Mode A (dry/manual), Mode B (fixture), Mode C (live-approved)
- [ ] **Run input package defined** (Section 4): 6 expected files with validation steps
- [ ] **Execution path defined** (Section 5): Entry point, parameters, steps, non-requirements
- [ ] **Required output artifacts listed** (Section 6): 9 mandatory, 2 optional, with verification criteria
- [ ] **Artifact policy defined** (Section 7): 6 core rules, acceptable conventions, prohibited behaviors
- [ ] **Post-run validation checklist exists** (Section 8): 21 checks across 7 categories
- [ ] **Source Quality Report verification defined** (Section 9): 10 checks across 3 categories
- [ ] **Founder Review Package verification defined** (Section 10): 10 checks across 3 categories
- [ ] **Failure handling defined** (Section 11): 7 general rules, 8 failure classes, post-failure procedure
- [ ] **Operational run notes defined** (Section 12): 12 fields to capture
- [ ] **Handoff to founder review defined** (Section 13): 6 artifacts, 6 rules, 8-item handoff checklist
- [ ] **Dry-run minimum acceptance defined** (Section 14): Minimum targets, acceptance rules, ideal targets
- [ ] **Full operational run acceptance defined** (Section 15): Targets and quality gates
- [ ] **Do not proceed rules defined** (Section 16): 7 blocking conditions
- [ ] **No implementation directives**: Document is operational procedure only
- [ ] **No live API authorization**: Live collection is gated behind founder approval
- [ ] **No source code, test, script, or artifact modifications**

---

## 18. Definition of Done

Item 6 is done when:

- [ ] **6.1** Pilot Run Procedure exists at `docs/decisions/pilot_run_procedure_v2_13.md`.
- [ ] **6.2** Preconditions are explicit: 13 items listed.
- [ ] **6.3** Run modes are explicit: Mode A (dry/manual), Mode B (fixture), Mode C (live-approved), with mode selection table.
- [ ] **6.4** Execution path is defined: entry point reference, parameters, steps, non-requirements.
- [ ] **6.5** Required artifacts are listed: 9 mandatory, 2 optional.
- [ ] **6.6** Validation checklist exists: 21 post-run checks (Section 8).
- [ ] **6.7** Source Quality Report verification exists: 10 checks (Section 9).
- [ ] **6.8** Founder Review Package verification exists: 10 checks (Section 10).
- [ ] **6.9** Failure handling exists: 7 rules, 8 failure classes, post-failure procedure (Section 11).
- [ ] **6.10** Handoff to founder review defined: handoff package, rules, checklist (Section 13).
- [ ] **6.11** Dry-run minimum acceptance defined (Section 14).
- [ ] **6.12** Full operational run acceptance defined (Section 15).
- [ ] **6.13** Do not proceed rules defined (Section 16).
- [ ] **6.14** `.\scripts\dev-git-check.ps1` passes.
- [ ] **6.15** One local commit exists with message: `[v2.13] 6 define pilot run procedure`.

---

*Pilot Run Procedure v2.13. Operational procedure document. Does not authorize live collection. Does not authorize committed runtime artifacts. Does not modify source code, tests, scripts, or pipeline behavior.*
