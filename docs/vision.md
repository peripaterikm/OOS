# Opportunity Operating System (OOS) — Vision

## 1. Purpose

Opportunity Operating System (OOS) is an AI-native operating system for systematically discovering, framing, stress-testing, validating, and managing a portfolio of business opportunities.

OOS is **not**:
- a generic idea generator,
- a motivational startup assistant,
- a theater of “AI directors” talking to each other,
- a classical consulting workflow hidden behind AI.

OOS **is**:
- a pain-first discovery engine,
- a hypothesis factory,
- a portfolio management system for business opportunities,
- a structured validation system,
- a compounding knowledge system that learns from both promising ideas and failed ideas.

The system is designed for a solo founder or very small team that wants to:
- discover real-world pains,
- turn them into structured opportunities,
- generate constrained business models,
- quickly reject weak ideas,
- design cheap validation tests,
- manage opportunities as a portfolio,
- accumulate “kill knowledge” as a moat.

---

## 2. Core Principle

**Pain-first, not tech-first.**

The system does not begin with:
- “where can I use AI?”
- “what model is trendy?”
- “what startup sounds cool?”

It begins with:
- recurring pains,
- broken workflows,
- manual workarounds,
- regulatory/platform shifts,
- underserved operational frictions,
- weak or absent software in real domains.

Technology is a response to discovered pain, not the source of the opportunity.

---

## 3. Primary User

The primary user profile is:

- solo founder or tiny team,
- capable of building software or coordinating its creation,
- wants high-leverage opportunities,
- wants recurring revenue potential,
- wants to avoid founder-time-dependent service work,
- prefers digital intake + standardized workflows + partner/externalized execution where needed,
- values structured thinking over random inspiration.

---

## 4. What OOS Does

OOS converts weak and fragmented market information into structured decisions.

High-level flow:

1. Detect raw signals from the outside world  
2. Validate whether signals represent real pain or just noise  
3. Frame validated signals as Opportunity Cards  
4. Generate constrained business-model variants  
5. Screen and kill weak ideas early  
6. Extract hypotheses and cheapest-next tests  
7. Run multi-perspective review on shortlisted opportunities  
8. Manage all opportunities as a portfolio  
9. Feed real-world validation back into future discovery and screening  
10. Graduate only the most promising opportunities into execution mode

---

## 5. Architectural Philosophy

### 5.1 Stateless agents, stateful system
Agents should not be the source of truth.

The system memory lives in artifacts:
- signals,
- opportunity cards,
- hypotheses,
- experiments,
- evidence,
- decisions,
- kill reasons,
- execution outcomes.

This keeps the system:
- auditable,
- inspectable,
- debuggable,
- less dependent on hidden chat context.

### 5.2 Orchestrator-centered workflow
The system uses a lightweight **orchestrator**.

The orchestrator:
- runs pipeline stages in order,
- chooses the appropriate model for each stage,
- saves artifacts,
- routes outputs into the right storage,
- prepares outputs for review.

The orchestrator is not a strategist.  
It is a workflow and routing layer.

### 5.3 Model routing by task type
Different tasks require different model classes.

Typical routing logic:
- cheap models → signal extraction, deduplication, rough classification
- medium models → framing, screening, portfolio review
- strong models → ideation, hypothesis mapping, council synthesis

This is both a cost-control mechanism and a system design principle.

---

## 6. Core Layers of OOS

### 6.1 Signal Layer
Collects raw signals from selected sources:
- forums,
- Reddit,
- reviews,
- complaints,
- changelogs,
- regulatory sources,
- niche communities,
- public structured datasets.

Signal Layer is not just ingestion.  
It also applies signal validity checks.

### 6.2 Opportunity Layer
Transforms signals into structured Opportunity Cards.

Each Opportunity Card captures:
- the pain,
- the target segment,
- possible opportunity type,
- possible economic significance,
- early pattern matches,
- potential business model direction.

### 6.3 Ideation Layer
Generates business-model variants based on:
- the opportunity,
- founder constraints,
- monetization patterns,
- standardization requirements,
- solo-founder feasibility.

The goal is not idea abundance.  
The goal is high-quality constrained business options.

### 6.4 Screen Layer
Acts as a hard kill filter.

Weak ideas should die here, before expensive thinking is wasted on them.

### 6.5 Hypothesis Layer
Extracts:
- key assumptions,
- critical uncertainties,
- cheapest tests,
- success/failure signals.

This layer turns ideas into validation plans.

### 6.6 Council Layer
Provides asymmetrical pressure-testing from different angles:
- Skeptic
- Assumption Auditor
- Pattern Matcher
- Chair / Synthesizer

This layer exists to expose fragility, not to produce polite average opinions.

### 6.7 Portfolio Layer
Manages all active, parked, killed, and graduated opportunities as a portfolio rather than as isolated ideas.

### 6.8 Kill Archive
Stores failed ideas and the reasons they died.

This is a strategic asset, not just a graveyard.

### 6.9 Execution Layer
Only for opportunities that have survived enough validation and are promoted into build mode.

This layer is intentionally outside the immediate v1 core.

---

## 7. Key Entities

The system should operate around these first-class objects:

- `Signal`
- `OpportunityCard`
- `IdeaVariant`
- `Hypothesis`
- `Experiment`
- `Evidence`
- `CouncilDecision`
- `PortfolioState`
- `KillReason`
- `ExecutionOutcome`
- `GraduationRecord`

These entities should be explicit in storage and in system logic.

---

## 8. Signal Validity

A raw signal is not automatically a valid business pain signal.

A signal is evaluated across five dimensions:

1. **Specificity** — concrete task or workflow problem, not vague complaining  
2. **Recurrence** — repeated across people or contexts  
3. **Active workaround** — evidence that people already patch the problem manually  
4. **Cost signal** — evidence of time, money, lost revenue, or risk  
5. **ICP match** — signal comes from a relevant target segment

Interpretation:
- `validated` = 3 or more dimensions met
- `weak` = 2 dimensions met
- `noise` = 0–1 dimensions met

Routing:
- validated → main pipeline
- weak → watchlist / weak-signal backlog
- noise → `noise_archive` with explicit rejection reason

---

## 9. Screen Philosophy

The screen is intentionally harsh.

An idea is killed if:
- it fails at least 2 of the mandatory checks, or
- it matches any immediate anti-pattern.

Mandatory checks:
1. The pain is real and recurring  
2. The ICP is identifiable and plausibly able to pay  
3. The solution can be sold as a product/system, not just as a custom service  
4. The market is not structurally closed to a new wedge  
5. The founder can start without being blocked by regulatory gatekeeping

Immediate anti-patterns:
1. Requires custom development or custom handling per client → disguised consulting  
2. Core value depends on founder presence → founder bottleneck by design  
3. Monetization depends mainly on traffic aggregation / ad model → weak unit economics  
4. No clear repeatable workflow → bespoke craft business risk

---

## 10. Council Philosophy

The council is **asymmetric**, not balanced.

It is designed to create productive tension and surface fragility.

### Roles
- **Skeptic** — identify likely death scenarios
- **Assumption Auditor** — identify the least-proven but most critical assumption
- **Pattern Matcher** — compare to prior failures in Kill Archive
- **Chair / Synthesizer** — integrate outputs into a decision

### Suspiciously clean rule
If the Skeptic finds 0–1 credible kill candidates, the memo is marked:
- `suspiciously_clean = true`

This always requires human review.

---

## 11. Portfolio Logic

The portfolio is managed through explicit states:

- `Active`
- `Parked`
- `Killed`
- `Graduated`

The goal is not to maximize the number of ideas.  
The goal is to maximize:
- the number of worth-testing opportunities,
- the speed of killing weak ideas,
- the quality of surviving hypotheses,
- the accumulation of useful knowledge.

---

## 12. Kill Archive as Strategic Asset

The Kill Archive stores:
- why an idea died,
- what assumption failed,
- what the hidden fragility was,
- what pattern it resembled,
- what future ideas should be penalized because of that knowledge.

Over time, this becomes a compounding moat:
- fewer repeated mistakes,
- better future screening,
- faster rejection,
- stronger pattern intelligence.

---

## 13. Feedback Loop from Execution into Discovery

In later versions, OOS should include `ExecutionOutcome`.

ExecutionOutcome captures:
- which experiment or pilot ran,
- whether it validated, invalidated, or partially validated the idea,
- what was surprising,
- which pattern tags mattered,
- what assumption turned out to be false,
- what failure mode appeared.

This allows the system to improve future discovery and screening through structured real-world evidence.

This feedback should be **semi-automatic** at first:
- the system can recommend score/weight adjustments,
- the owner confirms or rejects them.

---

## 14. Weekly Operating Rhythm

The system is designed for a weekly cadence:

### Overnight batch
- sensing,
- framing,
- ideation,
- screening,
- hypothesis mapping,
- council review,
- portfolio review.

### Morning review
The owner spends a focused session:
- reviewing summaries,
- approving or rejecting priorities,
- confirming kill decisions,
- deciding which experiments are worth running,
- deciding what gets parked or graduated.

This concentrates human attention into a controlled decision window.

---

## 15. v1 vs Long-Term Vision

### v1
A lean, disciplined discovery and validation core:
- signals
- opportunity cards
- ideation
- screen
- hypothesis mapping
- portfolio review
- kill archive
- basic orchestrator
- artifact store

### v2
Add:
- execution transition,
- execution outcomes,
- feedback loop,
- richer routing,
- stronger portfolio intelligence,
- UI / DB if needed.

### v3
Become a full Opportunity Operating System:
- self-learning,
- extensible research engine,
- broader portfolio platform,
- potentially multi-user / venture-studio mode.

---

## 16. Final Definition

**Opportunity Operating System is an AI-native system for discovering, structuring, stress-testing, validating, and managing a portfolio of business opportunities — with pain-first discovery, disciplined screening, cheap validation design, and compounding knowledge from both wins and failures.**