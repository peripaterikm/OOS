# OOS Roadmap v2.3 MVP Execution Overlay

## Purpose

This temporary execution overlay accelerates OOS toward a working Source Intelligence MVP while preserving `docs/roadmaps/OOS_roadmap_v2_3_source_intelligence_checklist.md` as the source of truth.

The overlay changes execution sequencing and GitHub checkpoint cadence only. It does not replace Roadmap v2.3 acceptance criteria, safety rules, validation requirements, or Dev Ledger updates.

## MVP Goal

Create the first working Source Intelligence loop:

```text
RawEvidence
-> classified evidence
-> CandidateSignal
-> weekly discovery CLI lite
-> founder discovery package lite
-> optional meaning-loop dry run
```

## MVP Included Items

- `5.1` Evidence cleaner and classifier
- `5.2` Evidence-to-signal extraction and scoring
- `6.2` Weekly discovery CLI lite
- `7.1` Founder Discovery Package lite
- `8.1` Existing meaning-loop integration dry run lite / optional

## Deferred Items

- Full `6.1` Source Yield Analytics
- Full `7.2` Traceability/compliance hardening
- Reddit collector implementation
- Dashboards and scorecards
- Additional sources
- Advanced scoring
- Live-network operating mode
- v2.3 completion checkpoint

## Local-Only Workflow

- Work on one long-lived local MVP branch: `feat/source-intelligence-mvp-discovery-loop`.
- Make one local commit after each completed roadmap item.
- Do not push, create PRs, merge, tag, or create releases until explicitly instructed.
- Run validation after each local commit package before advancing the roadmap item.
- Continue updating Roadmap v2.3 and the Dev Ledger per completed item.
- Perform a GitHub checkpoint only after the MVP slice is working and the owner explicitly requests it.

## Success Definition

A command should eventually exist that can run a discovery loop from available fixture/offline `RawEvidence` or fixture/offline collectors and produce a founder-readable package.

The MVP succeeds when that loop is deterministic, fixture-safe, source-traceable, and runnable without live internet/API calls, live LLM calls, secrets, or new dependencies.
