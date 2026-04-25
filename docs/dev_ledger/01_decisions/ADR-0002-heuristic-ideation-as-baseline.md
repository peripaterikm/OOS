# ADR-0002: Heuristic Ideation As Baseline

## Status

Accepted

## Context

OOS had deterministic heuristic ideation before Roadmap v2.2 AI meaning work.

## Decision

Heuristic ideation is baseline, fallback, and control group only. It is not the primary intelligence layer.

It is useful for placeholder output, pipeline plumbing tests, deterministic fallback, and comparing future LLM-assisted output against a known baseline.

## Consequences

- Heuristic idea artifacts must be clearly labeled by generation mode.
- Strong opportunity discovery should not be attributed to the heuristic path.
- Future LLM ideation work should compare against the heuristic baseline honestly.

