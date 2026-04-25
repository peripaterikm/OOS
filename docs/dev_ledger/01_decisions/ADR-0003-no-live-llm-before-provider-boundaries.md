# ADR-0003: No Live LLM Before Provider Boundaries

## Status

Accepted

## Context

Roadmap v2.2 adds several AI-shaped stages: signal understanding, clustering, contradiction detection, opportunity framing, ideation, and critique.

## Decision

Do not add live LLM/API calls before each stage has contracts, provider/stub boundaries, validation, traceability, metadata, and fallback behavior.

## Consequences

- Tests use deterministic stubs or static provider payloads.
- Modules must be compatible with future provider calls without requiring live network access now.
- Live LLM/API integration is deferred until the surrounding reliability envelope exists.

