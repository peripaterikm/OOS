# Source Registry and Allowlist Policy

**Version:** source_allowlist_policy.v1
**Roadmap:** v2.11 item 3
**Status:** Policy finalized / implementation pending
**Depends on:**
- [`discovery_source_adapter_contract.md`](discovery_source_adapter_contract.md) (v2.11 item 1)
- [`raw_evidence_artifact_schema.md`](raw_evidence_artifact_schema.md) (v2.11 item 2)
- [`source_url_traceability_contract.md`](source_url_traceability_contract.md) (v2.7 item 1.1)
**Registry file:** [`config/source_registry.json`](../../config/source_registry.json)
**Precedes:**
- Roadmap v2.11 items 4–7 — Source-specific hardening and feasibility plans

---

## 1. Scope

### 1.1 What the Source Registry Is

The **source registry** ([`config/source_registry.json`](../../config/source_registry.json)) is the canonical, static listing of every discovery source candidate known to OOS. It serves as:

- A **planning seed** — the registry records which sources are candidates, what their status is, and what conditions must be satisfied before they may be implemented or enabled.
- A **policy gate** — the registry does not itself authorize implementation, enable live access, or admit sources to the default weekly run. It records the conditions that must be met.
- A **single source of truth** — the registry is the authoritative list of source IDs, source types, and approved access methods. No source may be introduced into the OOS pipeline without a registry entry.

### 1.2 What the Allowlist Controls

The **allowlist policy** (this document) defines the rules that govern:

- **Registration** — when a source candidate may be added to the registry.
- **Authorization** — what gates must be passed before a source may be implemented in code.
- **Enablement** — what gates must be passed before a source may participate in live fetching or the default weekly run.
- **Suspension** — when a source must be paused or disabled.
- **Removal** — when a source must be removed from the registry.
- **Deferral / Rejection** — when a source must be deferred to a later roadmap or rejected outright.

### 1.3 Key Distinctions

The following terms are distinct and must not be conflated:

| Term | Meaning | Who Authorizes |
|------|---------|---------------|
| **Registered** | An entry exists in `source_registry.json`. | This item (v2.11 item 3) creates the seed registry. Future additions require separate approval. |
| **Authorized for implementation** | Source adapter code may be written. | Explicit founder approval. Registry presence does NOT authorize implementation. |
| **Enabled** | Source may be invoked in `live_opt_in` mode by an operator. | Separate founder approval after implementation, fixture tests, and controlled smoke. |
| **Live-enabled** | Source may make live external API calls. | Separate founder approval after controlled smoke with live data. |
| **Default-enabled** | Source participates in the default weekly run without manual opt-in. | Separate founder approval after sustained smoke evidence and quality report. |

**Default state for all v2.11 sources:** registered, NOT authorized, NOT enabled, NOT live-enabled, NOT default-enabled.

---

## 2. Relationship to Previous Contracts

### 2.1 Discovery Source Adapter Contract (v2.11 item 1)

The [adapter contract](discovery_source_adapter_contract.md) defines **how** a source adapter must work — its interface, lifecycle, fetch modes, error handling, and output contract. The allowlist policy defines **which** adapters may exist and **under what conditions** they may operate.

| Concern | Owned By |
|---------|----------|
| Adapter interface, fetch modes, error classification | Adapter contract (item 1) |
| Source identity, status, authorization gates | Allowlist policy (item 3, this document) |
| Field mapping to `RawEvidence` | Both: adapter contract specifies fields; registry records access methods |

### 2.2 Raw Evidence Artifact Schema (v2.11 item 2)

The [raw evidence artifact schema](raw_evidence_artifact_schema.md) defines **what shape** adapter output must take — the JSON artifact format, field schemas, validation rules, and deduplication policy. The allowlist policy defines **which sources** are permitted to produce raw evidence artifacts and under what conditions artifact generation may occur.

| Concern | Owned By |
|---------|----------|
| Artifact JSON structure, validation rules | Raw evidence schema (item 2) |
| Which sources may generate artifacts | Allowlist policy (item 3, this document) |
| `source_type` enum values | Both: schema defines values; registry assigns them to sources |

### 2.3 Source URL Traceability Contract (v2.7 item 1.1)

The [source URL traceability contract](source_url_traceability_contract.md) defines the **propagation guarantee** — every downstream artifact must carry real, stable source URLs. The allowlist policy enforces the **upstream gate**: no source may be registered, authorized, or enabled that cannot produce stable source URLs.

The traceability contract's placeholder URN policy (`urn:oos:*` forbidden) is binding on all sources in this registry. Every source entry carries `stable_source_url_required: true` and `source_url_policy: mandatory_external_url` as the first and non-negotiable gate.

---

## 3. Source Lifecycle States

Every source in the registry has a `status` field indicating its position in the lifecycle. The defined states are:

### 3.1 State Definitions

| State | Meaning | Who May Transition | Next State |
|-------|---------|-------------------|------------|
| `proposed` | Source candidate suggested but not yet assessed. No feasibility work done. | Founder / roadmap planning | `feasibility_required` or `rejected` |
| `feasibility_required` | Source requires a feasibility assessment before any connector planning. | Roadmap item authorizing feasibility study | `planned_connector`, `planned_hardening`, or `deferred` |
| `planned_hardening` | Existing adapter exists; hardening plan is authorized or in progress. | Roadmap item authorizing hardening plan | `implemented_fixture_only` |
| `planned_connector` | New source; connector implementation is authorized. | Founder approval after feasibility report | `implemented_fixture_only` |
| `implemented_fixture_only` | Adapter code exists and fixture tests pass. No live access yet. | Founder approval for controlled smoke | `controlled_smoke_only` |
| `controlled_smoke_only` | Controlled smoke tests pass with live data. Not yet default-enabled. | Founder approval for manual enablement | `enabled_manual` |
| `enabled_manual` | Source may be invoked manually via `live_opt_in`. Not in default weekly run. | Founder approval + sustained smoke evidence | `enabled_default` |
| `enabled_default` | Source participates in the default weekly run automatically. | — | `suspended` (if conditions degrade) |
| `suspended` | Source temporarily disabled due to policy violation, rate-limit issues, or quality degradation. | Founder review | `enabled_manual` or `deferred` |
| `deferred` | Source intentionally excluded from current roadmap. Requires separate review. | Founder / roadmap planning | Any state after separate review |
| `rejected` | Source permanently excluded. Reason documented. | Founder | Terminal state |

### 3.2 State Transitions

State transitions are **manual and documented**. No automated process may change a source's status in the registry. Every transition must:

1. Be recorded in a commit with a clear message referencing the authorizing decision.
2. Satisfy the gate conditions for the target state.
3. Be approved by the founder for any transition that enables live access or default run inclusion.

### 3.3 Current State of v2.11 Sources

| Source | Current Status | Next Status | Gating Item |
|--------|---------------|-------------|-------------|
| `hacker_news` | `planned_hardening` | `implemented_fixture_only` | v2.11 item 4 hardening plan + founder approval |
| `github_issues` | `planned_hardening` | `implemented_fixture_only` | v2.11 item 5 hardening plan + founder approval |
| `product_hunt` | `feasibility_required` | `planned_connector` | v2.11 item 6 feasibility report + founder approval |
| `pimenov_ai` | `feasibility_required` | `planned_connector` | v2.11 item 7 feasibility report + founder approval |
| All deferred sources | `deferred` | Requires separate review | v2.12+ |

---

## 4. Authorization Policy

### 4.1 Registry Presence Does Not Authorize Implementation

A source entry in `source_registry.json` is a **planning record**, not an implementation authorization. The registry records that a source is a candidate, describes its characteristics, and notes what conditions must be met. It does not grant permission to write code, call APIs, or modify the pipeline.

### 4.2 Roadmap Planning Does Not Authorize Implementation

The v2.11 roadmap (items 1–10) produces contracts, plans, feasibility assessments, and runbooks. None of these deliverables authorize writing connector, collector, or adapter code. Roadmap items 4–7 produce hardening plans and feasibility reports — they do not implement the connectors themselves.

### 4.3 Implementation Requires Explicit Founder Approval

Before any source adapter code is written:

1. The source must have a completed feasibility assessment or hardening plan (as applicable).
2. The plan must be reviewed by the founder.
3. The founder must explicitly approve the transition from planning to implementation.
4. The approval must be recorded (commit message, decision document, or run report).

### 4.4 Live Access Requires Separate Approval

Even after implementation, live access requires a separate, explicit approval:

1. Fixture tests must pass deterministically.
2. Controlled smoke tests must pass with live data.
3. Rate-limit and auth policies must be documented.
4. The founder must explicitly approve `live_access_allowed: true`.

### 4.5 Default Weekly Run Inclusion Requires Controlled Smoke Evidence

Before a source transitions to `enabled_default`:

1. The connector must be implemented.
2. Fixture tests must pass.
3. Multiple controlled smoke runs must complete without failure.
4. A source quality report must exist and show healthy metrics.
5. Noise must be below configured threshold or adequate filters must exist.
6. Source URL validation must be clean (no placeholders, no missing URLs).
7. Founder approval must be recorded.

---

## 5. Allowlist Rules

Every source, present and future, must satisfy these rules. A source that cannot satisfy any rule must remain at or be moved to `deferred` or `rejected`.

### 5.1 Mandatory Rules

| # | Rule | Applies To |
|---|------|------------|
| **R1** | No source without a stable `source_url` pattern. | Registration |
| **R2** | No source without deterministic fixture tests. | Implementation |
| **R3** | No source without a source quality summary. | Enablement |
| **R4** | No source without an explicit, non-changing `source_id`. | Registration |
| **R5** | No broad scraping of any source. | All states |
| **R6** | No source where ToS/robots compliance is unclear. | Registration, Enablement |
| **R7** | No live API calls in unit tests. | Implementation, Testing |
| **R8** | No default-enabled source without sustained smoke evidence. | Default run inclusion |

### 5.2 Source URL Rules

Per [`source_url_traceability_contract.md`](source_url_traceability_contract.md):

- Every source must have a defined, stable URL pattern for its items.
- `source_url` values must use `http://` or `https://` scheme with a valid hostname.
- No `urn:oos:*` placeholders. Ever.
- No source that cannot produce canonical, direct links to its source items.
- Fixture URLs must be stable and deterministic.

### 5.3 Fixture Requirements

Per the [adapter contract](discovery_source_adapter_contract.md) Section 9:

- Every source must have deterministic fixture files.
- Fixtures must be representative of real source data.
- Fixtures must not contain secrets, API keys, or PII.
- Fixture output must be byte-identical between runs.
- Snapshot tests must validate fixture determinism.

### 5.4 Access Method Requirements

- Every source must declare its access method(s) in the registry (`likely_access_methods`).
- Access methods must be specific: API endpoint, RSS feed, sitemap allowlist, static file — not "scraping" or "crawling."
- Broad crawling is prohibited. Each source must have a narrow, defined access surface.
- Auth tokens must use environment variables (never hardcoded).

---

## 6. Risk Classification

### 6.1 Risk Levels

| Risk Level | Criteria | Examples |
|------------|----------|----------|
| **Low** | Stable API, clear ToS, low noise, simple auth, deterministic fixtures straightforward | Well-documented public API with no auth required |
| **Low-to-Medium** | Stable access pattern but moderate noise, or auth complexity, or content considerations | Curated content source with static access |
| **Medium** | API with rate limits requiring careful handling, moderate noise, auth required, some content quality variance | Hacker News (noise), GitHub Issues (rate limits, auth), Product Hunt (API auth TBD) |
| **High** | Unclear ToS, scraping risk, high noise, fragile access, paywall, auth complexity, legal exposure | Reddit (ToS/API changes), LinkedIn (ToS prohibition), broad web crawl |

### 6.2 Risk Dimensions

Each source is assessed on these dimensions:

| Dimension | Low Risk | Medium Risk | High Risk |
|-----------|----------|-------------|-----------|
| **Legal / ToS risk** | Clear permissive ToS, API documented as public | ToS permissive but requires careful reading | ToS unclear, prohibits scraping, or requires legal review |
| **API stability** | Versioned API with deprecation policy | Stable but undocumented or single-provider | No API; scraping only; site structure changes frequently |
| **Auth / rate limit complexity** | No auth or simple API key | OAuth or token rotation required; moderate rate limits | Complex auth; severe rate limits; paywall |
| **Noise level** | Curated or inherently high-signal | Moderate noise; filters available | High noise; no effective filters possible |
| **Source URL stability** | Permanent, canonical URLs | Stable but may change (e.g., slugs) | Ephemeral URLs; no canonical form |
| **Access fragility** | Redundant access methods available | Single access method; documented fallback | Single fragile access; no fallback; site may disappear |
| **Content copyright concerns** | Public domain or explicitly permissive | Reasonable excerpting allowed | Full-text reproduction prohibited; paywall |

### 6.3 Current Source Risk Assignments

| Source | Risk Level | Primary Risk Factors |
|--------|-----------|---------------------|
| `hacker_news` | Medium | Noise level, content quality variance |
| `github_issues` | Medium | Rate limits, auth requirement, PR filtering |
| `product_hunt` | Medium | API auth TBD, signal is solution-pattern not pain |
| `pimenov_ai` | Low-to-Medium | Russian-language content, curation bias, update frequency unknown |
| `reddit` | High (deferred) | ToS/API changes, noise, legal review |
| `review_sites` | High (deferred) | ToS risk, scraping barriers |
| `job_boards` | High (deferred) | ToS barriers, structured data unclear |
| `linkedin_x_telegram` | High (deferred) | ToS prohibition, API restrictions, legal review |
| `broad_web_crawl` | High (deferred) | ToS risk, noise, legal exposure, no defined access surface |

---

## 7. Source Categories and Allowed Initial Entries

### 7.1 Active Registry Candidates (v2.11)

The v2.11 seed registry contains four active source candidates:

#### 7.1.1 Hacker News (`hacker_news`)

- **Category:** Discussion source
- **Status:** `planned_hardening`
- **Access methods:** HN Algolia Search API, HN official Firebase API
- **Signal type:** User-reported pains, workflow frustrations, "Ask HN" / "Show HN" posts
- **Risk:** Medium (noise, content quality variance)
- **Existing adapter:** [`src/oos/hn_algolia_collector.py`](../../src/oos/hn_algolia_collector.py)
- **Next step:** Hardening plan (v2.11 item 4)

#### 7.1.2 GitHub Issues (`github_issues`)

- **Category:** Issue tracker source
- **Status:** `planned_hardening`
- **Access methods:** GitHub REST API, GitHub Search API
- **Signal type:** Bug reports, feature requests, workaround descriptions, integration pain
- **Risk:** Medium (rate limits, auth, PR filtering)
- **Existing adapter:** [`src/oos/github_issues_collector.py`](../../src/oos/github_issues_collector.py)
- **Next step:** Hardening plan (v2.11 item 5)

#### 7.1.3 Product Hunt (`product_hunt`)

- **Category:** Product launch / solution pattern source
- **Status:** `feasibility_required`
- **Access methods:** Product Hunt GraphQL API (proposed)
- **Signal type:** Solution-pattern signals, launch trends, founder-targeted problems
- **Risk:** Medium (API auth TBD, signal classification nuance)
- **Existing adapter:** None
- **Next step:** Feasibility assessment (v2.11 item 6)
- **Note:** This is a solution-signal/product-pattern source, not a pure pain source. Downstream classification must account for this difference.

#### 7.1.4 pimenov.ai (`pimenov_ai`)

- **Category:** Curated expert / context source
- **Status:** `feasibility_required`
- **Access methods:** RSS (if available), sitemap (if available), static page allowlist
- **Signal type:** AI use-case patterns, trend context, idea-expansion evidence
- **Risk:** Low-to-Medium (Russian-language content, curation bias, update frequency)
- **Existing adapter:** None
- **Next step:** Feasibility assessment (v2.11 item 7)
- **Note:** No broad scraping. Only safe/static/RSS/sitemap-based access. Russian-language content with UTF-8 guarantee.

### 7.2 Deferred Source Groups (v2.12+)

The following source groups are registered in the `deferred_sources` block with `status: deferred`. They are excluded from v2.11 implementation. Each requires a separate technical, legal, and access review before any status change.

| Deferred Group | Includes | Primary Deferral Reason |
|---------------|----------|------------------------|
| `reddit` | Reddit posts, comments, subreddits | API changes, ToS, noise management |
| `review_sites` | G2, Capterra, Trustpilot, etc. | ToS review; scraping risk; paywall/authentication barriers |
| `job_boards` | LinkedIn Jobs, Indeed, Glassdoor, etc. | Scraping risk; ToS barriers; structured data access unclear |
| `linkedin_x_telegram` | LinkedIn, Twitter/X, Telegram | API access restrictions; legal review required; ToS prohibition |
| `broad_web_crawl` | General web crawling, search engine scraping | No defined access surface; ToS risk; noise; legal exposure |

---

## 8. Live Access Policy

### 8.1 Fixture Mode Is Default

- All unit tests and default validation MUST use `fixture` mode.
- `fetch_mode: fixture` is the default for every source adapter invocation.
- No test in the default test suite may make live network calls.

### 8.2 Live Mode Must Be Opt-In

- `live_opt_in` mode requires an explicit, deliberate action by the operator.
- An explicit CLI flag or configuration toggle must be set.
- No adapter may silently switch from fixture to live mode.
- No adapter may default to live mode.

### 8.3 Live Mode Must Not Run in Unit Tests

- Tests requiring live data must be gated behind explicit configuration.
- Such tests must be excluded from the default test suite.
- CI/CD pipelines must not run live-mode tests.

### 8.4 Credentials and Tokens

- Credentials/tokens must NOT be required for default validation.
- Auth tokens must use environment variables, never hardcoded values.
- No `.env` files, API keys, or tokens in versioned files.
- The `auth_token_env_var` configuration pattern (from the adapter contract) is mandatory.

### 8.5 Rate Limits

- Rate limit documentation is required before live smoke testing.
- Adapters must implement exponential backoff for transient failures.
- `Retry-After` and `X-RateLimit-*` headers must be respected.
- Rate limit exhaustion must be reported in the source quality summary.

---

## 9. Default Weekly Run Inclusion Policy

A source may be admitted to the default weekly run only after satisfying ALL of these gates:

### 9.1 Inclusion Gates

| # | Gate | Evidence Required |
|---|------|-------------------|
| **G1** | Connector implemented | Source adapter code exists and is reviewed |
| **G2** | Fixture tests pass | Deterministic fixture tests pass with identical output across runs |
| **G3** | Controlled smoke passes | Multiple controlled smoke runs complete without failure |
| **G4** | Source quality report exists | Report shows healthy metrics per source quality scoring contract (v2.11 item 8) |
| **G5** | Noise below threshold or filters exist | Noise rate is acceptable per source type, or adequate filters are in place |
| **G6** | Source URL validation clean | No placeholder URLs, no missing URLs, all URLs traceable |
| **G7** | Founder approval recorded | Explicit approval documented in commit or decision record |

### 9.2 Gating Order

Gates must be satisfied in order. G1–G2 are implementation gates. G3–G6 are quality gates. G7 is the final approval gate. No gate may be skipped.

### 9.3 No Source Is Default-Enabled in v2.11

All sources in the v2.11 seed registry have `default_enabled: false`. No source will be default-enabled during v2.11. Default enablement is a v2.12+ concern, contingent on completing all hardening and feasibility items plus the source quality scoring and controlled smoke infrastructure (items 8–9).

---

## 10. Rejection and Deferral Policy

### 10.1 When to Reject

A source candidate should be **rejected** (status: `rejected`, terminal state) when:

- No stable `source_url` pattern exists or can be constructed.
- The source has no canonical item URLs (ephemeral content only).
- ToS explicitly prohibit all forms of automated access.
- `robots.txt` disallows all relevant paths and no API exists.
- The source is paywalled with no practical access path.
- The noise level is so high that no feasible filter can extract signal.
- The source is fundamentally the wrong signal type for OOS (e.g., pure entertainment).

### 10.2 When to Defer

A source candidate should be **deferred** (status: `deferred`) when:

- ToS/robots compliance is unclear and requires legal review.
- API access is prohibitively expensive or restricted.
- Auth/rate limit complexity exceeds current implementation capacity.
- The source category requires infrastructure not yet built (e.g., real-time streaming).
- The source is valuable but lower priority than active roadmap items.
- A deterministic fixture path is not yet clear but may become clear later.

### 10.3 Deferral Is Not Rejection

Deferred sources remain in the registry under `deferred_sources`. They are not forgotten. They are intentionally excluded from the current roadmap with a documented reason. Each deferred source group must be re-assessed in the roadmap where it is next considered.

### 10.4 No Silent Deferral

Every source that moves to `deferred` or `rejected` must have a documented reason in the registry. The reason must be specific enough that a future reviewer can understand why the decision was made and what would need to change for reconsideration.

---

## 11. Validation Policy

### 11.1 Validation for v2.11 Item 3

This item (v2.11 item 3) is a docs/config planning item. Validation expectations are:

1. **`config/source_registry.json` is valid JSON** — parseable, well-formed, all required fields present.
2. **`docs/contracts/source_allowlist_policy.md` exists** — all required sections present and internally consistent.
3. **No source/test/script modifications** — only the two deliverable files plus the roadmap checklist update.
4. **`.\scripts\dev-git-check.ps1` passes** — the standard pre-commit validation script.
5. **`git status --short` shows only expected files** — `config/source_registry.json`, `docs/contracts/source_allowlist_policy.md`, and the roadmap checklist.
6. **No live calls** — no API calls, no LLM calls, no network access during validation.

### 11.2 Ongoing Registry Validation (Future)

When the registry is wired into runtime behavior (v2.12+), validation will include:

- Registry JSON schema validation against a defined schema.
- Cross-reference checks: every source referenced in code must exist in the registry.
- Status consistency: no source with `status: implemented_fixture_only` may make live calls.
- Policy compliance: every `default_enabled` source must have passed all inclusion gates.

These validations are **not implemented** in v2.11 item 3. The registry is a static seed only.

---

## 12. Non-Goals

This item (v2.11 item 3) and this policy explicitly **exclude**:

| Non-Goal | Rationale |
|----------|-----------|
| Implementing source registry loader | Registry is a static file; no loader code is authorized |
| Implementing source adapters | Items 4–7 produce plans, not implementations |
| Enabling live APIs for any source | All sources have `live_access_allowed: false` |
| Enabling default source runs | All sources have `default_enabled: false` |
| Adding scraping infrastructure | Prohibited by default policy and risk gates |
| Adding Reddit, review sites, job boards | All deferred to v2.12+ |
| Adding LinkedIn, X/Twitter, Telegram | All deferred to v2.12+ |
| Adding broad web crawl | Prohibited; deferred with explicit rejection rationale |
| Adding LLM extraction to discovery | Not in v2.11 scope |
| Modifying existing collector code | Existing HN and GitHub collectors are read-only for this item |
| Wiring registry into runtime | Static planning seed only; no runtime integration |
| Creating test fixtures for new sources | Implementation concern; not in docs/config item |

---

## 13. Decision

**v2.11 item 3 creates the source registry seed and the allowlist policy only.**

- `config/source_registry.json` is created as a static planning/config seed with four active source candidates and five deferred source groups.
- `docs/contracts/source_allowlist_policy.md` (this document) defines the rules governing source registration, authorization, enablement, and lifecycle.
- No runtime behavior is changed.
- No connector implementation is authorized.
- No live API access is authorized.
- No default weekly run inclusion is authorized.
- All sources default to disabled, fixture-only, with no live access.
- Founder approval is required before any source transitions from its current status.
- Deferred sources require separate technical, legal, and access review before any status change.

---

## 14. Self-Audit

| Question | Answer |
|----------|--------|
| Did this avoid implementation? | **Yes.** Contract/policy only. No `.py` files modified. |
| Did this avoid source/test changes? | **Yes.** No source, test, script, or example files changed. |
| Did this define what the source registry is? | **Yes.** Section 1.1. |
| Did this define what the allowlist controls? | **Yes.** Section 1.2. |
| Did this define key distinctions (registered/authorized/enabled/live-enabled/default-enabled)? | **Yes.** Section 1.3. |
| Did this define relationship to previous contracts? | **Yes.** Section 2 covers adapter contract, raw evidence schema, and source URL traceability. |
| Did this define source lifecycle states? | **Yes.** Section 3 defines 11 states with transition rules. |
| Did this define authorization policy? | **Yes.** Section 4 states registry does not authorize implementation; founder approval required. |
| Did this define allowlist rules? | **Yes.** Section 5 defines 8 mandatory rules. |
| Did this define risk classification? | **Yes.** Section 6 defines 3 levels and 7 dimensions. |
| Did this document initial registry candidates? | **Yes.** Section 7 covers 4 active candidates and 5 deferred groups. |
| Did this define live access policy? | **Yes.** Section 8 covers fixture-first, opt-in live, no-live-in-tests, credentials, rate limits. |
| Did this define default weekly run inclusion policy? | **Yes.** Section 9 defines 7 gates. |
| Did this define rejection/deferral policy? | **Yes.** Section 10 defines when to reject vs defer. |
| Did this define validation policy? | **Yes.** Section 11 covers this item's validation and future validation. |
| Did this state non-goals explicitly? | **Yes.** Section 12 lists 12 explicit non-goals. |
| Did this state the decision clearly? | **Yes.** Section 13. |
| Did the source registry file have all required fields? | **Yes.** `config/source_registry.json` includes registry_version, registry_status, roadmap, created_for_item, implementation_authorized_by_this_file, founder_approval_required_for_implementation, default_policy, sources, deferred_sources, notes. |
| Did the source registry include all required sources? | **Yes.** hacker_news, github_issues, product_hunt, pimenov_ai as active; reddit, review_sites, job_boards, linkedin_x_telegram, broad_web_crawl as deferred. |
| Did all entries have correct status and metadata? | **Yes.** Each entry has source_id, source_type, source_name, status, implementation_authorized, default_enabled, live_access_allowed, unit_test_mode, likely_access_methods, stable_source_url_required, source_url_policy, risk_level, notes. |
| Did this avoid wiring registry into runtime? | **Yes.** Registry is static seed only; explicitly stated in notes and non-goals. |
| Did this avoid authorizing implementation? | **Yes.** implementation_authorized_by_this_file: false; founder_approval_required_for_implementation: true. |

---

*Source Registry and Allowlist Policy. v2.11 item 3. Policy finalized / implementation pending.*
