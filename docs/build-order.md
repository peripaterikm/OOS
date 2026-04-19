# Opportunity Operating System (OOS) — Build Order

## Build Philosophy

Build OOS as a disciplined core system, not as a sci-fi platform.

Principles:
- core before extensions,
- artifacts before UI,
- kill logic before elegance,
- pipeline before autonomy theater,
- evidence before ambition.

The build order below assumes an 8-week first implementation path.

---

# Week 1 — Project Foundation and Documentation

## Objective
Create a clean implementation base and establish the project as a documentation-driven build.

## Deliverables
- repository structure
- docs folder
- configuration conventions
- environment handling
- logging/error conventions
- basic CLI entrypoint or runner structure
- a stable place for artifacts

## Tasks
1. Create repo/project structure
2. Add core docs:
   - `docs/vision.md`
   - `docs/scope-v1.md`
   - `docs/build-order.md`
3. Define configuration files or settings module
4. Create base runner / orchestrator skeleton
5. Define artifact directories
6. Add basic smoke-test command

## Done when
- the project has a stable structure,
- docs are source-of-truth,
- a base runner exists,
- artifacts can be written and inspected.

---

# Week 2 — Core Data / Artifact Model

## Objective
Implement the first-class entities of the system.

## Deliverables
Typed schemas or structured models for:
- Signal
- OpportunityCard
- IdeaVariant
- Hypothesis
- Experiment
- Evidence
- CouncilDecision
- PortfolioState
- KillReason

## Tasks
1. Implement artifact schemas/models
2. Add serialization/deserialization
3. Define validation rules
4. Add unit tests for entity validity
5. Ensure UTF-8 and structured storage work correctly

## Done when
- all core artifacts exist as explicit objects,
- they can be stored and read,
- validation catches malformed data.

---

# Week 3 — Signal Layer

## Objective
Build signal ingestion and signal validation logic.

## Deliverables
- raw signal ingestion
- signal validity scoring
- status routing:
  - validated
  - weak
  - noise
- `noise_archive`
- weak-signal backlog/watchlist

## Tasks
1. Implement signal ingestion interface
2. Implement 5-dimension signal validity evaluation
3. Add scoring and classification rules
4. Route signals into proper destinations
5. Add rejection reasons for noise
6. Add tests for borderline cases

## Done when
- signals are ingested,
- each signal gets structured validity output,
- noise is archived explicitly,
- weak signals are preserved rather than lost.

---

# Week 4 — Opportunity Framing and Screen Layer

## Objective
Transform validated signals into Opportunity Cards and kill weak idea variants early.

## Deliverables
- opportunity framing logic
- idea variant generation stub or initial implementation
- screen kill checklist
- anti-pattern detection
- pass/park/kill output

## Tasks
1. Implement Opportunity Card creation
2. Add opportunity type support if useful
3. Implement constrained idea-variant generation interface
4. Implement Screen mandatory checks
5. Implement Screen anti-pattern kills
6. Store kill reasons
7. Add tests for disguised-consulting and founder-bottleneck cases

## Done when
- validated signals can become Opportunity Cards,
- ideas can be screened,
- weak ideas are killed with explicit reasons,
- no silent failures exist.

---

# Week 5 — Hypothesis Layer

## Objective
Turn surviving ideas into testable business hypotheses.

## Deliverables
For each surviving idea:
- critical assumptions
- most fragile assumption
- cheapest-next test
- 7-day test plan
- 14-day test plan
- success criteria
- kill criteria

## Tasks
1. Implement hypothesis extraction flow
2. Implement experiment object structure
3. Add mapping from idea → assumptions → experiment design
4. Define success/failure metrics structure
5. Test output quality on several example opportunities

## Done when
- surviving ideas produce concrete validation steps,
- hypotheses are explicit,
- experiments are small and testable.

---

# Week 6 — Asymmetric Council

## Objective
Add adversarial and asymmetrical review.

## Deliverables
Council roles:
- Skeptic
- Assumption Auditor
- Pattern Matcher
- Chair / Synthesizer

Plus:
- suspiciously_clean flag

## Tasks
1. Implement Skeptic memo
2. Implement Assumption Auditor memo
3. Implement Pattern Matcher using current kill archive
4. Implement Chair synthesis
5. Add suspiciously_clean rule
6. Store council outputs as artifacts

## Done when
- every shortlisted idea can be pressure-tested,
- council outputs are structured,
- suspiciously clean ideas are flagged.

---

# Week 7 — Portfolio Layer and Weekly Review

## Objective
Turn the system into a portfolio manager rather than a one-off analyzer.

## Deliverables
- portfolio registry/state
- Active / Parked / Killed / Graduated transitions
- weekly portfolio summary
- review-ready output package

## Tasks
1. Implement portfolio state store
2. Add transition rules
3. Add weekly summary generation
4. Surface what needs founder review
5. Connect kills into Kill Archive
6. Add regression tests for state transitions

## Done when
- multiple opportunities can exist simultaneously,
- state transitions work,
- the system can produce a weekly review package.

---

# Week 8 — Stabilization and v1 Operational Loop

## Objective
Run the full v1 cycle end to end and harden weak points.

## Deliverables
- orchestrator-driven end-to-end batch flow
- model routing rules
- stable artifact writing
- review package
- v1 readiness report

## Tasks
1. Connect all stages into one orchestrated flow
2. Add simple model routing by stage
3. Run at least several full dry runs
4. Audit artifact consistency
5. Audit kill quality
6. Audit council usefulness
7. Fix obvious over-complexity
8. Write v1 operational checklist

## Done when
- the full weekly opportunity cycle can run,
- artifacts are coherent,
- founder can review output in one session,
- v1 is ready for real use.

---

# v2 Build Direction (Not for immediate build)

Only after v1 proves useful:

## Add
- ExecutionOutcome entity
- feedback loop from execution to discovery
- semi-automatic weighting recommendations
- richer portfolio intelligence
- UI / database if operationally necessary
- execution transition layer

## Do not add before v1 proves itself
- full self-learning
- multi-user productization
- advanced ontology/knowledge graph
- complex autonomous agent swarms
- dashboard-first development

---

# Practical Build Rules

## Rule 1
If signal quality is weak, do not add more features.  
Fix Signal Layer first.

## Rule 2
If too many ideas survive screening, Screen is too weak.  
Make it harsher.

## Rule 3
If council outputs are vague or polite, asymmetry is too weak.  
Strengthen failure-oriented prompts.

## Rule 4
If portfolio review feels like clutter, too many weak ideas are entering Active state.  
Tighten earlier layers.

## Rule 5
If the system starts to look more impressive than useful, stop and simplify.

---

# Core v1 Acceptance Checklist

v1 is acceptable when:

- raw signals are ingested and classified,
- invalid/noisy signals are explicitly routed away,
- validated signals become structured opportunities,
- weak ideas are killed with explicit reasons,
- surviving ideas produce concrete hypotheses and tests,
- council pressure-tests shortlisted ideas,
- portfolio states are tracked,
- kill archive is updated,
- one full weekly cycle can run coherently.

---

# Final Instruction for Development

Build OOS as a **useful weekly operating system for opportunity discovery and validation**, not as a demo of AI sophistication.

The standard of success is:
- better decisions,
- faster kills,
- clearer experiments,
- lower founder confusion,
- compounding opportunity intelligence.