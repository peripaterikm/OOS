# First Real Open-Source Signal Run v1

## Goal

Use the completed Roadmap v2.4 Source Intelligence stack to run a small real open-source signal pass and produce founder-review artifacts.

## Scope

- Execute a bounded live run with existing Hacker News Algolia and GitHub Issues collectors.
- Use existing query planning, candidate signal extraction, price signal extraction, weak-pattern handling, kill archive warning output, and founder package rendering.
- Record a repeatable operating protocol and run report.
- Keep runtime artifacts outside tracked source control.

## Why This Matters After v2.4

Roadmap v2.4 completed the signal-quality and AI-layer contracts. This operational run checks whether those capabilities are usable on a small real evidence batch before moving into the v2.5 Evidence Pack Layer.

## Intentionally Not Implemented

- No new collectors.
- No new scoring, filtering, or architecture changes.
- No Reddit, Facebook, LinkedIn, scraping-heavy source, or paid API usage.
- No live LLM/API calls.
- No dependency changes.

## Relationship To v2.5

The run provides practical input for v2.5 by showing which evidence fields, traceability links, price hints, ambiguity notes, and founder-package sections are ready to be packaged into stronger review evidence.

## Acceptance Criteria

- Protocol document exists.
- Bounded real live run is executed with HN and GitHub Issues.
- Run report records commands, limits, source counts, artifact paths, and quality assessment.
- Founder package artifact is generated or failure is recorded clearly.
- Top candidate signals are summarized for founder review.
- Runtime artifacts leave no tracked git changes.
- Safe validation passes after the run.
- No live LLM/API calls are made.
