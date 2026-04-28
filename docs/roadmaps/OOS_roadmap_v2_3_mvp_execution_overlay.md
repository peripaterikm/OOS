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

## Current MVP Progress

- `5.1` Evidence cleaner and classifier is complete locally on `feat/source-intelligence-mvp-discovery-loop`.
- `5.2` Evidence-to-signal extraction and scoring is complete locally on `feat/source-intelligence-mvp-discovery-loop`.
- `6.2-lite` weekly discovery CLI is complete locally on `feat/source-intelligence-mvp-discovery-loop`.
- `7.1-lite` Founder Discovery Package is complete locally on `feat/source-intelligence-mvp-discovery-loop`.
- `8.1-lite` meaning-loop dry run is complete locally on `feat/source-intelligence-mvp-discovery-loop`.
- MVP slice implementation is complete locally; next deferred roadmap target is full `6.1` Source Yield Analytics unless the owner requests the GitHub checkpoint first.
- Full `6.1` Source Yield Analytics remains deferred until after the MVP loop can run end to end.
- Full `7.2` Traceability/compliance hardening remains deferred until after the MVP loop can run end to end.

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

As of `8.1-lite`, the local MVP branch can run the fixture/offline loop through an adapter-only meaning-loop dry run and produce founder-readable package artifacts plus meaning-loop compatibility artifacts. The GitHub checkpoint remains deferred until explicitly requested.

## MVP+1 Live Collection Mode

### Purpose

The MVP+1 extension adds an explicit, bounded live collection mode for the weekly discovery CLI while preserving fixture/offline mode as the default.

Roadmap v2.4 now owns live signal quality hardening after initial MVP+1 live collection. Item `1.1` covers HTML/entity cleanup, UTF-8 decode hardening, `ai_cfo_smb` relevance gating, anti-marketing downgrades, more discriminative deterministic scoring, finance-specific HN/GitHub query templates, and safe RSS feed URL handling.

### Command

```powershell
.\.venv\Scripts\python.exe -m oos.cli run-discovery-weekly `
  --topic ai_cfo_smb `
  --project-root . `
  --run-id live_smoke_001 `
  --use-collectors `
  --allow-live-network `
  --max-total-queries 4 `
  --max-results-per-query 5 `
  --include-meaning-loop-dry-run
```

### Safety Flags

- Default weekly discovery still uses fixture/local `RawEvidence` input.
- `--use-collectors` switches the input stage to query planning, scheduling, and collector routing.
- `--allow-live-network` is required before live collectors may perform network calls.
- Live network therefore requires both `--use-collectors` and `--allow-live-network`.
- Query and result caps are explicit through `--max-total-queries`, `--max-queries-per-source`, `--max-queries-per-topic`, and `--max-results-per-query`.
- `--source-id` and `--source-type` can limit manual smoke runs to a specific source.

### Scope

- Live collector routing covers implemented Phase B collectors: HN Algolia, GitHub Issues, Stack Exchange, and RSS feeds.
- Reddit collector is not implemented.
- Trustpilot, Capterra, G2, LinkedIn, and GDELT collectors remain out of scope.
- Tests and validation remain fixture/mocked only and do not make internet/API calls.
- Manual live smoke is required before PR/release decisions.

### Manual Live Smoke

After the local commit, the owner may manually run the command above or a narrower first pass such as:

```powershell
.\.venv\Scripts\python.exe -m oos.cli run-discovery-weekly `
  --topic ai_cfo_smb `
  --project-root . `
  --run-id live_hn_smoke_001 `
  --use-collectors `
  --allow-live-network `
  --source-type hacker_news_algolia `
  --max-total-queries 1 `
  --max-results-per-query 3 `
  --include-meaning-loop-dry-run
```
