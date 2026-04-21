# AGENTS.md

## Project context

This repository contains:

- **OOS (Opportunity Operating System)** — a system for discovering, screening, validating, and managing business opportunities.
- **Pain Discovery Layer (PDL)** — a precursor layer that autonomously discovers pain signals from curated sources before they enter the main OOS pipeline.

The repository is documentation-driven. The `/docs` directory is the source of truth for architecture, scope, and build order.

## Working mode

You must work in **small, explicitly scoped implementation packages**.

Do NOT:
- redesign the architecture unless explicitly asked,
- refactor unrelated files,
- add UI unless explicitly requested,
- add a database unless explicitly requested,
- introduce “helpful” abstractions that are not justified by current scope,
- implement future roadmap items early.

Do:
- follow the documented build order,
- preserve UTF-8 everywhere,
- prefer deterministic and testable implementations,
- keep logic inspectable,
- return exact files changed and exact commands to run.

## Source of truth

Treat the following as authoritative, when present:

- `/docs/vision.md`
- `/docs/scope-v1.md`
- `/docs/build-order.md`
- Pain Discovery Layer specs and build-order docs in `/docs`
- configuration files in `/config`
- prompts in `/config/prompts`

If implementation and docs disagree, prefer the docs unless the user explicitly overrides them.

## OOS-specific rules

- Signals, opportunities, hypotheses, council decisions, portfolio states, and kill reasons are first-class artifacts.
- System memory lives in explicit artifacts/files, not hidden agent memory.
- Recurrence is **cluster-level**, not per-signal.
- Single validated signals are **manual-promote only**.
- Auto-promote is allowed only for qualified clusters.
- Low extractor confidence means the signal is **forced weak**, unless founder override exists.
- `KillReason` must explain why the idea died, not just label it.
- Council must stay structured, not devolve into free-form multi-agent roleplay.

## Pain Discovery Layer rules

Per-signal validation dimensions:
- specificity
- active_workaround
- cost_signal
- icp_match

Per-cluster metrics:
- signal_count
- avg_score
- distinct_source_ids_count
- temporal_spread_days

Promotion policy:
- manual promotion for validated singletons after founder review
- auto-promotion only for clusters that satisfy:
  - `signal_count >= 2`
  - `avg_score >= 3`

Priority boosters:
- `distinct_source_ids_count >= 2`
- `temporal_spread_days >= 7`

## Implementation discipline

For each requested task, return:

1. changed file list
2. exact commands to run
3. expected test output
4. short note on what the next step should be

When implementing, prefer:
- typed models
- structured file storage
- explicit validation
- narrow interfaces
- predictable CLI commands

## Safety and repository hygiene

Never:
- commit secrets,
- commit `.env`,
- commit `.venv`,
- commit generated `artifacts/` unless explicitly asked,
- commit `reports/` unless explicitly asked.

Preserve or improve:
- `.gitignore`
- tests
- project docs

## Preferred workflow

Default workflow:

1. read relevant docs
2. identify exact scope
3. implement only that scope
4. run tests
5. summarize output
6. stop

Do not continue to the next milestone automatically unless explicitly asked.
