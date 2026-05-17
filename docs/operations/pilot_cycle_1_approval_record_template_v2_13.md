# Pilot Cycle 1 — Approval Record

**Record ID:** `pilot_cycle_1_approval_record_v2_13`
**Run ID:** `<pilot_run_YYYY-MM-DD_XXXXXXXX>`
**Input Mode:** Mode A/B — Bounded Manual Input
**Created at:** `<ISO_8601_UTC_timestamp>`
**Template version:** v2.13

---

## 1. Approval Record Legend

| Status | Meaning |
|--------|---------|
| **APPROVED** | Founder has explicitly approved this action. Approval timestamp and notes recorded. |
| **NOT APPROVED** | Founder has explicitly declined or has not yet approved this action. Action is blocked. |
| **NOT REQUIRED** | This approval gate does not apply to the current run mode (Mode A/B bounded manual input). |
| **PENDING** | Approval has been requested but not yet granted. |

---

## 2. Approval Status Overview

| # | Gate | Description | Default Status | Current Status | Approved At | Approved By | Notes |
|---|------|-------------|---------------|---------------|-------------|-------------|-------|
| AG-1 | Live HN Collection | Explicit founder opt-in required before any live Hacker News API calls | **NOT APPROVED** | **NOT APPROVED** | — | — | Mode A/B does not require this approval. No live HN API calls are authorized. |
| AG-2 | Live GitHub Issues Collection | Explicit founder opt-in required before any live GitHub API calls | **NOT APPROVED** | **NOT APPROVED** | — | — | Mode A/B does not require this approval. No live GitHub API calls are authorized. |
| AG-3 | GitHub Repo Allowlist | Founder must review and approve the specific repositories before collection begins | **NOT APPROVED** | **NOT APPROVED** | — | — | Allowlist exists as a proposal only. Manual curation follows the proposed allowlist without requiring formal approval. |
| AG-4 | Stack Exchange Stretch | Must not be included in default pilot path; requires explicit founder approval | **NOT APPROVED** | **NOT APPROVED** | — | — | Stack Exchange / Stack Overflow are excluded. No records from this source are present. |
| AG-5 | Committing Runtime Pilot Artifacts | No runtime outputs committed to repository without explicit founder approval | **NOT APPROVED** | **NOT APPROVED** | — | — | All runtime outputs will be written to explicit `output_dir` only. No repository commits. |
| AG-6 | Starting Any Source Expansion | No additional sources beyond HN + GitHub Issues may be added | **NOT APPROVED** | **NOT APPROVED** | — | — | Source scope frozen at HN + GitHub Issues. No expansion authorized. |
| AG-7 | Go/No-Go Decision Finalization | Decision is founder-made, evidence-supported; must not be automated | **NOT APPROVED** | **PENDING** | — | — | This gate is addressed after founder review, not before pilot run. |

---

## 3. Detailed Approval Records

### AG-1: Live HN Collection

| Field | Value |
|-------|-------|
| **Status** | **NOT APPROVED** |
| **Reason** | Mode A/B bounded manual input is the selected run mode. No live HN Algolia API calls are needed or authorized. Manual collection from public HN URLs does not require API access. |
| **What would be required to approve** | Founder must explicitly request live HN collection for a future cycle. |
| **Impact of current status** | All HN evidence is collected manually from public HN pages. No API rate limits apply. All `source_url` values are real, verifiable HN item URLs. |
| **Approval checklist (not applicable)** | N/A for Mode A/B |
| **Date reviewed** | `<ISO_8601_UTC>` |
| **Reviewer** | `<founder_name>` |

### AG-2: Live GitHub Issues Collection

| Field | Value |
|-------|-------|
| **Status** | **NOT APPROVED** |
| **Reason** | Mode A/B bounded manual input is the selected run mode. No live GitHub Issues API calls are needed or authorized. Manual collection from public GitHub issue pages does not require API access. |
| **What would be required to approve** | Founder must explicitly request live GitHub Issues collection for a future cycle. |
| **Impact of current status** | All GitHub evidence is collected manually from public GitHub issue pages. No API rate limits apply. All `source_url` values are real, verifiable GitHub issue URLs. |
| **Approval checklist (not applicable)** | N/A for Mode A/B |
| **Date reviewed** | `<ISO_8601_UTC>` |
| **Reviewer** | `<founder_name>` |

### AG-3: GitHub Repo Allowlist

| Field | Value |
|-------|-------|
| **Status** | **NOT APPROVED** (formal approval not required for Mode A/B) |
| **Proposed allowlist** | 22 repos across 5 groups (A–E) as defined in [`github_issues_repo_allowlist_query_plan_v2_13.md`](../decisions/github_issues_repo_allowlist_query_plan_v2_13.md), Section 5 |
| **First-cycle subset** | 10 repos as defined in Section 6 of the same document |
| **Reason for NOT APPROVED** | Manual curation from public GitHub issue pages follows the proposed allowlist as guidance but does not require formal allowlist approval. Live collection would require AG-3 approval. |
| **What would be required to approve** | Founder must review and explicitly approve the repo allowlist before any live GitHub API calls. |
| **Date reviewed** | `<ISO_8601_UTC>` |
| **Reviewer** | `<founder_name>` |

### AG-4: Stack Exchange Stretch

| Field | Value |
|-------|-------|
| **Status** | **NOT APPROVED** |
| **Reason** | Stack Exchange / Stack Overflow is not included in the default pilot path. Pilot Cycle 1 Brief explicitly requires AG-4 approval for stretch inclusion. |
| **Impact of current status** | No Stack Exchange records are present in the input package. Source scope is limited to HN + GitHub Issues. |
| **What would be required to approve** | Founder must explicitly request Stack Exchange stretch inclusion and record the approval here. |
| **Date reviewed** | `<ISO_8601_UTC>` |
| **Reviewer** | `<founder_name>` |

### AG-5: Committing Runtime Pilot Artifacts

| Field | Value |
|-------|-------|
| **Status** | **NOT APPROVED** |
| **Reason** | Runtime pilot outputs must not be committed to the repository without explicit founder approval. All outputs are written to explicit `output_dir` only. |
| **Impact of current status** | No runtime artifacts will be committed to the repository. The `output_dir` is selected outside committed repository paths. |
| **What would be required to approve** | Founder must explicitly approve committing specific runtime artifacts to the repository after the pilot run completes and artifacts are reviewed. |
| **Date reviewed** | `<ISO_8601_UTC>` |
| **Reviewer** | `<founder_name>` |

### AG-6: Starting Any Source Expansion

| Field | Value |
|-------|-------|
| **Status** | **NOT APPROVED** |
| **Reason** | Source expansion is deferred to v2.14+ and conditional on a Go decision. No additional sources beyond HN + GitHub Issues may be added to Pilot Cycle 1. |
| **Impact of current status** | Source scope is frozen. Any record with a `source_id` other than `hacker_news` or `github_issues` is rejected as a gate violation. |
| **What would be required to approve** | A Go or Conditional Go decision, followed by founder approval of a specific source expansion plan. |
| **Date reviewed** | `<ISO_8601_UTC>` |
| **Reviewer** | `<founder_name>` |

### AG-7: Go/No-Go Decision Finalization

| Field | Value |
|-------|-------|
| **Status** | **PENDING** (addressed after founder review) |
| **Reason** | The Go/No-Go decision requires: (1) a completed pilot run with validated outputs, (2) founder review per the [Founder Review Protocol v2.13](../decisions/founder_review_protocol_v2_13.md), and (3) founder's final judgment. It cannot be made before the pilot runs. |
| **Impact of current status** | The pilot run can proceed but no Go/No-Go decision can be recorded. The decision direction is advisory only. |
| **Expected date** | After founder review completes (within 48 hours of pilot run handoff) |
| **Date reviewed** | `<ISO_8601_UTC>` |
| **Reviewer** | `<founder_name>` |

---

## 4. Approval Summary Matrix

| Gate | Required for Mode A/B? | Current Status | Blocks Pilot Run? | Blocks Founder Review? | Blocks Go/No-Go? |
|------|------------------------|---------------|-------------------|----------------------|-----------------|
| AG-1: Live HN Collection | No (Mode A/B is manual) | NOT APPROVED | No | No | No |
| AG-2: Live GitHub Collection | No (Mode A/B is manual) | NOT APPROVED | No | No | No |
| AG-3: GitHub Repo Allowlist | No (Mode A/B uses proposed list as guidance) | NOT APPROVED (formal) | No | No | No |
| AG-4: Stack Exchange Stretch | No (excluded by default) | NOT APPROVED | No | No | No |
| AG-5: Committing Runtime Artifacts | No (outputs go to `output_dir`) | NOT APPROVED | No | No | No |
| AG-6: Source Expansion | No (scope is frozen) | NOT APPROVED | No | No | No |
| AG-7: Go/No-Go Finalization | Yes — but after review | PENDING | No | No | Yes — blocks finalization |

**Current pilot run status:** All gates blocking the pilot run (AG-1 through AG-6) are either NOT REQUIRED for Mode A/B or have no blocking impact. The pilot run can proceed. AG-7 (Go/No-Go finalization) is addressed after founder review.

---

## 5. Additional Approvals (None Requested)

No additional approvals beyond the seven standard gates have been requested for Pilot Cycle 1.

| # | Action | Approval Required? | Status |
|---|--------|-------------------|--------|
| 1 | Exceeding collection caps | Yes (founder) | NOT REQUESTED — caps are within bounds |
| 2 | Single-source-only input | No (must document why) | NOT APPLICABLE — both sources represented |
| 3 | Modifying pipeline code | Forbidden (docs-only item) | NOT REQUESTED |

---

## 6. Approval Record Integrity

| Check | Status |
|-------|--------|
| All 7 approval gates documented | [ ] Confirmed |
| All live/source expansion approvals default to NOT APPROVED | [ ] Confirmed |
| Mode A/B gates correctly marked as NOT REQUIRED for pilot run | [ ] Confirmed |
| AG-7 correctly marked as PENDING (post-review) | [ ] Confirmed |
| Approval timestamps recorded where applicable | [ ] Confirmed |
| Reviewer identity recorded where applicable | [ ] Confirmed |
| No gate is APPROVED without explicit founder action | [ ] Confirmed |

---

*Approval Record Template v2.13. Defaults all live/source expansion approvals to NOT APPROVED. Does not authorize live APIs, source expansion, or artifact commits. Fill reviewer names and timestamps after founder review.*
