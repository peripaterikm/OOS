# Opportunity Operating System (OOS) — Scope v1

## 1. v1 Objective

Build the smallest useful version of OOS that can:

1. ingest and validate raw pain signals,
2. convert them into structured Opportunity Cards,
3. generate constrained business-model variants,
4. kill weak ideas early,
5. map surviving ideas into testable hypotheses,
6. review opportunities as a portfolio,
7. accumulate reasons why ideas die.

The goal of v1 is **not** to build a full autonomous venture platform.  
The goal is to create a disciplined discovery and validation core that produces better opportunity decisions with low founder-time overhead.

---

## 2. What v1 Must Achieve

A successful v1 should allow a solo founder to run a repeatable weekly opportunity cycle and get:

- a batch of validated signals,
- a small set of framed opportunities,
- a filtered shortlist of business-model variants,
- explicit assumptions and experiments,
- a portfolio summary,
- explicit kill decisions,
- a growing anti-portfolio archive.

---

## 3. In Scope for v1

### 3.1 Core pipeline
v1 includes these layers:

1. **Signal Layer**
2. **Opportunity Layer**
3. **Ideation Layer**
4. **Screen Layer**
5. **Hypothesis Layer**
6. **Council Layer (simplified asymmetric form)**
7. **Portfolio Layer**
8. **Kill Archive**

### 3.2 Core entities
v1 must explicitly support:

- `Signal`
- `OpportunityCard`
- `IdeaVariant`
- `Hypothesis`
- `Experiment`
- `Evidence` (basic form)
- `CouncilDecision`
- `PortfolioState`
- `KillReason`

### 3.3 Signal validity
v1 must implement signal scoring across:
- specificity,
- recurrence,
- active workaround,
- cost signal,
- ICP match.

It must classify signals into:
- `validated`
- `weak`
- `noise`

And route them into:
- main pipeline,
- weak-signal backlog,
- noise archive.

### 3.4 Screen kill logic
v1 must implement:
- mandatory checks,
- anti-pattern kills,
- explicit kill reasons.

### 3.5 Simplified Council
v1 council must be asymmetric and minimal:
- Skeptic
- Assumption Auditor
- Pattern Matcher
- Chair / Synthesizer

### 3.6 Portfolio states
v1 must support:
- Active
- Parked
- Killed
- Graduated

### 3.7 Weekly operating cadence
v1 is designed around:
- batch processing,
- periodic review,
- explicit approval / rejection decisions.

### 3.8 Artifact store
v1 should keep system truth in explicit artifacts/files or equivalent structured storage.
Conversation history is not the source of truth.

### 3.9 Orchestrator
v1 includes a lightweight orchestrator that:
- runs pipeline stages,
- applies routing logic,
- persists artifacts,
- prepares review outputs.

### 3.10 Model routing
v1 includes simple routing rules:
- cheap / medium / strong model assignment by stage

No dynamic self-optimization is required.

---

## 4. Out of Scope for v1

The following are intentionally excluded:

### 4.1 Full execution system
Do not build:
- PM swarm,
- Builder swarm,
- Outreach swarm,
- Analyst swarm,
- autonomous shipping pipeline.

### 4.2 Full self-learning
Do not implement:
- automated weight re-training,
- auto-promoted retrospectives,
- autonomous policy updates,
- generalized learning engine.

### 4.3 Full platformization
Do not build:
- multi-user platform,
- SaaS account system,
- collaboration layer,
- billing,
- customer-facing dashboards.

### 4.4 Heavy UI before core logic
A simple CLI or minimal internal interface is acceptable.  
A polished product UI is not required in v1.

### 4.5 Overbuilt agent architecture
Do not build:
- agent theater,
- many-role freeform conversations,
- dynamic multi-agent debate systems,
- unnecessary orchestration complexity.

### 4.6 Advanced knowledge graph
Do not build a full semantic graph/ontology engine in v1.

### 4.7 Fully automatic feedback loop
Execution-to-discovery feedback is a v2 topic.

---

## 5. v1 Success Criteria

v1 is successful if it can, on a regular cadence:

- process raw signals,
- reject obvious noise,
- frame meaningful opportunities,
- produce a shortlist of worth-testing ideas,
- explain why weak ideas were killed,
- output cheap validation plans,
- help the owner decide what to test next,
- accumulate useful kill knowledge.

### Anti-metric
The system is **not** successful just because it generates many ideas.

A good v1:
- kills fast,
- narrows fast,
- produces clear next actions,
- avoids disguised consulting traps.

---

## 6. Signal Layer Spec

### Inputs
- forums
- reviews
- complaint sources
- changelogs
- communities
- manually added signals

### Outputs
Each signal should include at minimum:
- source
- timestamp
- raw content
- extracted pain statement
- candidate ICP
- signal validity dimensions
- signal validity score
- signal status
- rejection reason if routed to noise

### Rules
- score validity across the 5 required dimensions
- route weak/noise explicitly
- do not silently discard rejected signals

---

## 7. Opportunity Layer Spec

### Inputs
- validated signals
- optionally weak signals promoted by manual review

### Outputs
`OpportunityCard` with:
- title
- source signals
- pain summary
- ICP
- opportunity type
- why this might matter
- early monetization possibilities
- initial notes

The goal is to transform raw pain into a structured opportunity object.

---

## 8. Ideation Layer Spec

### Inputs
- Opportunity Cards
- founder constraints
- pattern library

### Outputs
Multiple constrained idea variants per opportunity.

Each idea variant should include:
- short concept
- business model angle
- where standardization lies
- where AI leverage lies
- where external execution may be needed
- rough monetization model

The ideation layer must remain constrained.
No generic “AI assistant for everyone” ideas.

---

## 9. Screen Layer Spec

### Kill logic
An idea is killed if:
- it fails at least 2 mandatory checks, or
- it matches any anti-pattern.

### Mandatory checks
1. Pain is real and recurring
2. ICP is identifiable and can plausibly pay
3. Solution can be productized/systematized
4. Market is not structurally closed to a new wedge
5. Founder can start without being blocked by regulatory gatekeeping

### Anti-patterns
1. Custom development / custom handling per client
2. Founder bottleneck by design
3. Monetization dependent on traffic aggregation / ads
4. No clear repeatable workflow

### Required outputs
For each screened idea:
- pass / park / kill
- explicit rationale
- which checks failed
- which anti-patterns matched

---

## 10. Hypothesis Layer Spec

For surviving ideas, v1 must produce:
- critical assumptions,
- most fragile assumption,
- cheapest-next test,
- 7-day test,
- 14-day test,
- success signals,
- kill criteria.

The purpose of this layer is to turn ideas into **validation actions**, not product fantasy.

---

## 11. Council Layer Spec

### Roles
- Skeptic
- Assumption Auditor
- Pattern Matcher
- Chair

### Required outputs
- likely kill scenarios
- least-proven critical assumption
- similarity to prior failed patterns
- final recommendation

### Rule
If Skeptic finds only 0–1 kill candidates:
- mark decision as `suspiciously_clean = true`

---

## 12. Portfolio Layer Spec

### States
- Active
- Parked
- Killed
- Graduated

### Required portfolio functions
- maintain list of opportunities by state
- allow movement between states
- summarize current portfolio
- surface what needs review
- surface what should be killed or promoted

### Review philosophy
Portfolio management is more important than idea count.
The system should privilege:
- fast elimination,
- concentrated focus,
- explicit decisions.

---

## 13. Kill Archive Spec

Each killed idea must store:
- idea identifier
- kill date
- kill reason
- failed assumptions
- anti-patterns matched
- notes on why it looked attractive but failed

Kill Archive is a v1 core asset, not an afterthought.

---

## 14. Technical Scope Guidance

v1 should prefer:
- simple file-based or straightforward structured persistence,
- simple CLI workflows,
- explicit artifacts,
- low hidden complexity.

v1 should avoid:
- complex distributed systems,
- unnecessary async orchestration,
- overbuilt agent debate layers,
- premature UI polish.

---

## 15. Human-in-the-loop Boundaries

The system can:
- collect,
- structure,
- screen,
- propose,
- summarize,
- recommend.

The founder decides:
- what is worth testing,
- when to override a weak signal,
- what gets graduated,
- whether suspiciously clean ideas should be reviewed manually.

---

## 16. v1 Exit Condition

v1 is complete when the system can reliably run a full weekly opportunity cycle and produce a portfolio review package with:

- validated signals,
- new opportunity cards,
- screened ideas,
- mapped hypotheses,
- council memos,
- portfolio state updates,
- kill archive updates.