# Mini-Epic - Source Intelligence Live Collection Mode

## Goal

Add an explicit, bounded live collection mode to the weekly discovery CLI so implemented collectors can collect real `RawEvidence` before the existing Source Intelligence pipeline runs.

## Scope

- Added collector-mode routing for weekly discovery.
- Added live-network gating and bounded collection limits.
- Added source-id and source-type filters.
- Added collector-mode summary and package metadata.
- Added focused mocked tests for live collection mode.
- Updated the MVP execution overlay and Dev Ledger state.

## Out Of Scope

- No Reddit collector.
- No Trustpilot, Capterra, G2, LinkedIn, or GDELT collectors.
- No live LLM/API calls.
- No new dependencies.
- No secrets or tokens.
- No usernames, handles, logins, display names, or bulk dumps stored by default.
- No internet/API calls during tests or validation.
- No push, PR, merge, tag, or release.

## Files Changed

- `src/oos/live_collection.py`
- `src/oos/discovery_weekly.py`
- `src/oos/cli.py`
- `tests/test_live_collection_mode.py`
- `docs/roadmaps/OOS_roadmap_v2_3_mvp_execution_overlay.md`
- `docs/dev_ledger/00_project_state.md`
- `docs/dev_ledger/02_mini_epics/live-collection-mode.md`
- `docs/dev_ledger/03_run_reports/live-collection-mode.md`

## CLI Flags

The weekly discovery CLI now supports:

- `--use-collectors`
- `--allow-live-network`
- `--max-total-queries`
- `--max-queries-per-source`
- `--max-queries-per-topic`
- `--max-results-per-query`
- `--source-id`
- `--source-type`
- existing `--include-meaning-loop-dry-run`

Default fixture mode remains unchanged.

## Live-Network Gating

Live network collection requires both:

```text
--use-collectors
--allow-live-network
```

Collector mode without `--allow-live-network` runs safely with live network disabled and returns a zero-evidence collector run unless fixture payloads are injected by tests or future tooling.

## Collector Routing Behavior

`src/oos/live_collection.py` maps implemented collector source types to collector classes:

- `hacker_news_algolia` -> `HNAlgoliaCollector`
- `github_issues` -> `GitHubIssuesCollector`
- `stack_exchange` -> `StackExchangeCollector`
- `rss_feed` -> `RSSFeedCollector`

Unsupported or failing collectors are recorded in `collection_errors` without killing the entire discovery run.

## Collection Limits

Collector runs use `CollectionLimits` and enforce:

- total scheduled query cap
- per-source query cap
- per-topic query cap
- per-query result cap
- optional source-id filter
- optional source-type filter

## Reporting Behavior

`discovery_run_summary.json` now includes collector-mode metadata:

- `collection_mode`
- `live_network_enabled`
- `query_plan_count`
- `scheduled_query_count`
- `collectors_attempted`
- `collectors_succeeded`
- `collectors_failed`
- `collection_errors`

The Markdown summary and Founder Discovery Package include collection mode and live-network status.

## Privacy Behavior

Collectors continue to map author identity to role/context only. Tests verify live-mode mocked outputs do not store raw GitHub logins. Existing HN, GitHub, Stack Exchange, and RSS collectors preserve safe metadata only.

## Validation Evidence

Validation is recorded in `docs/dev_ledger/03_run_reports/live-collection-mode.md`.

## Local-Only Note

This MVP+1 extension was implemented locally on `feat/source-intelligence-live-collection-mode`. Push and PR creation are deferred until the owner completes a manual live smoke and explicitly approves.

## Safety

- No push performed.
- No PR created.
- No merge performed.
- No tag created.
- No release created.
- No live internet/API calls made during tests or validation.
- No live LLM/API calls made.
