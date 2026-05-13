# Founder ICP and Preference Profile — v2.13 Pilot Cycle 1

**Title:** Founder ICP and Preference Profile v2.13
**Status:** Active — guiding v2.13 Pilot Cycle 1 review only
**Roadmap:** v2.13 Operational Pilot Go/No-Go
**Created:** 2026-05-13
**Schema version:** `founder_icp_preference_profile.v1`

---

## 1. Scope

This document defines the founder's Ideal Customer Profile (ICP), opportunity preferences, excluded markets, business relevance signals, noise definitions, review rubric, and decision guidance for v2.13 Pilot Cycle 1. It is a **review and interpretation guide**, not an implementation artifact. It does not modify pipeline code, scoring weights, or portfolio state.

---

## 2. Founder Opportunity Thesis

The founder is looking for **practical, validated, business-relevant opportunities where AI can create leverage**. Preference is for online-first, legally clean, scalable, relatively lightweight businesses that can be validated quickly.

Core beliefs:
- Pain-first discovery beats tech-first ideation.
- Real pains are specific, repeated, and have clear actors.
- Opportunities worth pursuing have reachable buyers and plausible validation paths.
- Noise is abundant; signal requires structured filtering.
- Killer opportunities come from observing broken workflows, not from reading hype.

---

## 3. Preferred ICPs (Ideal Customer Profiles)

### High Priority

| # | ICP | Description |
|---|-----|-------------|
| ICP-1 | **Small and medium business (SMB) owners** | People running businesses with 2–200 employees; operational pain; willing to pay for time savings |
| ICP-2 | **Finance teams / fractional CFOs / consultants** | Professionals handling reporting, reconciliation, forecasting, compliance |
| ICP-3 | **Operations managers** | People responsible for making workflows run; manual-process pain |
| ICP-4 | **Solo founders / small teams** | Builders who need leverage; technically capable; time-constrained |
| ICP-5 | **Developers building with AI agents** | Engineers working with agent frameworks, LLMs, automation; observability/debugging pain |
| ICP-6 | **Data analysts / automation-heavy teams** | People wrangling data pipelines, ETL, dashboards, manual reporting |
| ICP-7 | **Agencies and consultants serving SMB clients** | Service providers who see repeated client pain across many businesses |

### Medium Priority

| # | ICP | Description |
|---|-----|-------------|
| ICP-8 | **Creator / professional tool users** | Independent professionals needing better tools for their workflow |
| ICP-9 | **Internal tools teams** | Teams building tools for their own organization |
| ICP-10 | **B2B marketplace participants** | Only if demand-side pain is clearly evidenced |

### Low Priority

| # | ICP | Description |
|---|-----|-------------|
| ICP-11 | **Broad consumer app users** | Unfocused; monetization unclear; validation expensive |
| ICP-12 | **Entertainment / social consumers** | Not aligned with founder focus |
| ICP-13 | **Generic productivity app users** | "Another to-do list" — no specific workflow pain |

---

## 4. Preferred Opportunity Types

### Strong Preference

- B2B / prosumer SaaS
- AI workflow automation
- Tools for small and medium businesses
- Finance / accounting / management reporting / CFO workflows
- Data analysis / data operations / dashboards
- Devtools around AI agents, automation, debugging, observability, testing
- Operational tools that reduce manual work
- Vertical AI tools for clear professional workflows
- AI-powered middleman / orchestration businesses (if legally clean)

### Preferred Validation Shapes

Opportunities should be testable via:
- Customer interviews
- Manual concierge validation
- Landing page / waitlist
- Small pilot with real users

### Explicitly Deprioritized Shapes

- "AI wrapper with no workflow pain" — thin LLM wrappers without clear buyer problem
- Ideas requiring major upfront capital before validation
- Products requiring large sales teams before validation
- Consumer apps with unclear monetization
- Ideas dependent on network effects from day one
- Broad horizontal platforms without a sharp wedge

---

## 5. Excluded or Strongly Deprioritized Markets

These markets are **out of scope** for the founder. Signals from these domains should be treated as noise:

| # | Excluded Market | Reason |
|---|-----------------|--------|
| X-1 | Gambling | Ethical; not founder interest |
| X-2 | Adult content | Ethical; not founder interest |
| X-3 | Crypto speculation | Not a real-economy pain domain |
| X-4 | Gray-hat scraping / spam / lead-gen | Legally and ethically problematic |
| X-5 | Politically manipulative tools | Ethical |
| X-6 | Surveillance / spyware | Ethical |
| X-7 | Illegal or ToS-hostile automation | Legal risk |
| X-8 | Heavy healthcare / regulated medical workflows | Regulatory burden unless clearly non-clinical |
| X-9 | Products requiring major upfront capital | Cannot validate cheaply |
| X-10 | Products requiring large sales teams before validation | Not founder-fit |
| X-11 | Consumer apps with unclear monetization | Not founder interest |
| X-12 | Ideas dependent on network effects from day one | Cannot validate quickly |

---

## 6. Business Relevance Signals

These signals **increase** opportunity score. Evidence containing them should be weighted more heavily:

### Primary Relevance Signals

| # | Signal | Definition | Example |
|---|--------|------------|---------|
| S-1 | **Clear time loss** | Evidence describes hours/days lost to manual work | "I spend 5 hours/week on this manual reconciliation" |
| S-2 | **Manual repetitive work** | Work that is repeated regularly and done by hand | "Every month we export CSVs and merge them manually" |
| S-3 | **Money loss or revenue leakage** | Direct financial cost of the pain | "We lose ~$2k/month to billing errors" |
| S-4 | **Broken production workflow** | Workflow that blocks or degrades production output | "Our deployment pipeline breaks every time we add a new service" |
| S-5 | **Integration pain** | Pain caused by tools that don't work together | "We have 5 tools and none of them talk to each other" |
| S-6 | **Compliance / reporting burden** | Regulatory or internal reporting that is manual and painful | "SOC 2 evidence collection takes 3 days every quarter" |
| S-7 | **Repeated workaround** | Evidence of people building their own hacks/scripts | "I wrote a 200-line Python script just to sync these two systems" |
| S-8 | **Willingness to pay** | Explicit or implicit willingness to pay for a solution | "I'd gladly pay $200/month for something that fixes this" |
| S-9 | **Teams / customers affected** | Pain affects multiple people or external customers | "My whole team of 8 struggles with this daily" |
| S-10 | **Urgent operational problem** | Pain is blocking or actively causing damage | "We can't ship until we solve this" |
| S-11 | **Painful existing alternatives** | Current solutions are expensive, bad, or absent | "The only tool that does this costs $5k/month and is terrible" |
| S-12 | **People already trying to solve** | Evidence of active problem-solving attempts | "We tried building this internally but gave up" |

---

## 7. Noise / Banal Signal Definitions

These patterns indicate **low signal quality**. Evidence matching them should be treated as weak/noise:

| # | Noise Pattern | Definition | Example |
|---|---------------|------------|---------|
| N-1 | **Generic "AI would be cool for X"** | No specific pain, just AI enthusiasm | "AI could really help with project management" |
| N-2 | **Hype thread with no pain** | Discussion about trends, not problems | "The future of AI agents is going to be huge" |
| N-3 | **One-off bug with no recurrence** | Single incident, not a pattern | "Our deploy failed once last month" |
| N-4 | **Hobby-only complaint** | Pain in a hobby context, not business | "I wish my home lab dashboard was prettier" |
| N-5 | **Vague frustration (no actor/workflow/object)** | Frustration without specifics | "DevOps is so broken these days" |
| N-6 | **Launch / self-promo disguised as pain** | "We built X because Y is hard" — solution-first, not pain-first | "Check out our new AI debugging tool!" |
| N-7 | **Flamewar / meta-discussion** | Heated debate about tools/languages, not pain | "TypeScript vs JavaScript debate" |
| N-8 | **"Build another dashboard" with no buyer** | Dashboard idea without clear ICP or pain | "Someone should build a dashboard for X" |
| N-9 | **Purely technical curiosity** | Interesting technically but no business cost | "I wonder if you could use WebAssembly for this" |

---

## 8. Founder Review Rubric

Every candidate cluster or opportunity must be reviewed against these 10 questions:

| # | Question | What to Look For |
|---|----------|-----------------|
| R-1 | **Is the pain specific?** | Concrete actor, workflow, and problem — not abstract "X is hard" |
| R-2 | **Is the actor / buyer clear?** | Named role or segment; not "people" or "developers in general" |
| R-3 | **Is the workflow clear?** | Steps described; inputs and outputs understood |
| R-4 | **Is the pain repeated?** | Regular occurrence, not a one-off |
| R-5 | **Is there business cost?** | Time, money, or risk quantified or clearly implied |
| R-6 | **Can this be validated in 1–2 weeks?** | Interview, landing page, concierge — not "build MVP first" |
| R-7 | **Could someone pay for this?** | Willingness-to-pay evidence or strong inference |
| R-8 | **Is there a reachable ICP?** | Can the founder find and talk to these buyers? |
| R-9 | **Is this legally clean?** | No ToS hostility, gray areas, or regulatory nightmares |
| R-10 | **Is this interesting enough for the founder to spend time on?** | Founder motivation and expertise fit |

Rubric scoring (qualitative, not automated):
- **8–10 "yes"** → strong candidate; likely PROMOTE
- **5–7 "yes"** → promising but gaps; likely NEEDS_MORE_EVIDENCE or PARK
- **2–4 "yes"** → weak; likely PARK or KILL
- **0–1 "yes"** → banal/noise; KILL

---

## 9. Decision Guidance

### PROMOTE

Promote when ALL of these hold:
- Specific pain with clear actor and workflow
- Clear ICP from high or medium priority list
- Evidence from more than one source OR repeated evidence from one source
- Business cost visible (time, money, risk)
- Plausible validation path in 1–2 weeks
- Legally clean
- Founder interest

Signal characteristics: S-1 through S-12 present; N-1 through N-9 absent.

### NEEDS_MORE_EVIDENCE

Flag when:
- Interesting pain but evidence is thin (single source, low detail)
- Single-source but promising pattern
- ICP unclear but pain looks real
- Scoring promising but uncertainty high
- Missing willingness-to-pay signal
- Missing buyer clarity

### PARK

Park when:
- Moderately interesting but not urgent
- Unclear monetization path
- Not aligned with current founder focus
- Timing unclear but worth remembering
- Would be interesting in a different market cycle

### KILL

Kill when:
- Banal / generic pain (matches N-1 through N-9)
- High noise, no real signal
- No identifiable buyer
- No feasible validation path in 1–2 weeks
- Legally or ethically problematic
- Excluded market (matches X-1 through X-12)
- Too far from preferred domains with no redeeming signal
- Vendor promo / launch disguised as pain

KillReason must explain **why** the idea died, not just label it. Acceptable reasons include but are not limited to: `too_generic`, `no_buyer`, `vendor_promo_false_positive`, `no_real_pain`, `not_aligned`, `excluded_market`, `no_validation_path`, `founder_bottleneck`, `ethical_conflict`.

### REVISIT_LATER

Revisit when:
- Possibly interesting but timing unclear
- Market not ready (technology, regulation, adoption)
- Requires source expansion beyond current scope
- Depends on external trend that hasn't matured
- Would benefit from more data cycles

---

## 10. Pilot Cycle 1 Preference Focus

For the first pilot cycle, the following pain domains are the **primary focus**. Clusters and candidates in these areas should receive extra attention during review:

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

## 11. How This Profile Should Be Used by OOS

### During Pilot Cycle 1

1. **Signal extraction and scoring** — The existing deterministic pipeline runs as-is. This profile does not modify scoring weights.
2. **Cluster review** — When reviewing pain clusters, compare cluster themes against Sections 3–7 to assess relevance.
3. **Opportunity candidate review** — Evaluate each candidate against the rubric (Section 8) and decision guidance (Section 9).
4. **Founder review session** — The founder uses this profile as a reference during manual review of the founder review package.
5. **Decision recording** — Decisions (PROMOTE / PARK / KILL / NEEDS_MORE_EVIDENCE / REVISIT_LATER) are recorded with rationale referencing this profile.

### After Pilot Cycle 1

- If GO: this profile becomes the baseline for Cycle 2; it may be refined based on founder feedback from Cycle 1 review.
- If CONDITIONAL GO: profile is preserved; quality improvements in v2.14 may incorporate profile signals into scoring.
- If NO-GO: profile is preserved as documentation of founder intent; informs pipeline repair decisions.

### Relationship to Code

- The existing [`FounderPreferenceProfile`](src/oos/founder_preference_profile.py) dataclass in `src/oos/founder_preference_profile.py` is a **runtime artifact** built from actual founder decisions. This document is a **declarative, human-authored guide** that precedes those decisions. After pilot cycles generate founder decisions, the runtime profile can be compared against this document to detect drift.
- This document does **not** feed directly into scoring. It is a reference for human review.

---

## 12. Explicit Non-Goals

This profile does **not**:

- Create founder decisions automatically
- Mutate the opportunity portfolio
- Create `KillReason` records
- Authorize source expansion (deferred to Go decision)
- Authorize live source access (requires separate founder approval)
- Modify scoring weights in `src/oos/founder_preference_profile.py`
- Feed into automated ICP matching (not implemented in v2.13)
- Serve as a configuration file for the pipeline
- Replace the runtime [`FounderPreferenceProfile`](src/oos/founder_preference_profile.py) dataclass
- Define ICPs for markets the founder is not interested in

---

## 13. Self-Audit Checklist

- [x] **Preferred ICPs defined** (Section 3): 7 high-priority, 3 medium-priority, 3 low-priority
- [x] **Preferred opportunity types defined** (Section 4): SaaS, automation, devtools, data, finance, operations
- [x] **Excluded markets defined** (Section 5): 12 excluded categories with reasons
- [x] **Business relevance signals defined** (Section 6): 12 positive signals
- [x] **Noise/banal signals defined** (Section 7): 9 noise patterns
- [x] **Founder review rubric defined** (Section 8): 10 questions with qualitative scoring
- [x] **Decision guidance defined** (Section 9): 5 decision types with criteria
- [x] **Pilot Cycle 1 focus areas defined** (Section 10): 7 priority pain domains
- [x] **Usage instructions defined** (Section 11): How OOS uses this profile
- [x] **Non-goals explicit** (Section 12): What this profile does not do
- [x] **All sections present**: Title, Status, Scope, Thesis, ICPs, Opportunity Types, Excluded Markets, Relevance Signals, Noise Definitions, Review Rubric, Decision Guidance, Pilot Focus, Usage, Non-Goals, Self-Audit
- [x] **Document format supports downstream consumption**: structured tables, numbered signals, cross-referenceable identifiers
- [x] **No implementation directives**: document is declarative only

---

*Founder ICP and Preference Profile v2.13 — for use in Pilot Cycle 1 review only. Does not modify source code, tests, scripts, or pipeline behavior.*
