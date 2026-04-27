# Reddit Source Policy Amendment

## Goal

Amend Roadmap v2.3 and Source Intelligence architecture so Reddit is treated as a high-value default internal research source with guardrails, not as an excluded Phase D-only source.

## Decision

Reddit is now a Phase C controlled internal research source. It is enabled by default for standard discovery after a Reddit collector is implemented, but the Query Planner must not generate executable Reddit `QueryPlan` records while `collector_available=false`.

## Scope

- Update Source Intelligence architecture policy language.
- Update Roadmap v2.3 source policy language without advancing roadmap state.
- Add source-registry fields for default enablement, standard-discovery inclusion, collector availability, post-collector activation, and usage mode.
- Update Reddit default source policy and metadata.
- Add Query Planner safety gating for sources with unavailable collectors.
- Add focused tests for Reddit policy and planner behavior.

## Out Of Scope

- No Reddit collector.
- No current roadmap item advancement.
- No completed/remaining counter changes.
- No external/commercial productization review implementation.
- No internet/API calls.
- No live LLM calls.
- No dependencies.
- No secrets.
- No push, merge, tag, or release.

## Files Changed

- `docs/architecture/source_intelligence_layer_v0_3.md`
- `docs/roadmaps/OOS_roadmap_v2_3_source_intelligence_checklist.md`
- `src/oos/source_registry.py`
- `src/oos/query_planner.py`
- `tests/test_source_registry_query_planner.py`
- `docs/dev_ledger/00_project_state.md`
- `docs/dev_ledger/02_mini_epics/reddit-source-policy-amendment.md`
- `docs/dev_ledger/03_run_reports/reddit-source-policy-amendment.md`

## Policy Details

- `phase`: `Phase C - controlled internal research source`
- `enabled_by_default`: `true`
- `included_in_standard_discovery_runs`: `true`
- `collector_available`: `false` until a Reddit collector is implemented
- `active_after_collector_implementation`: `true`
- `usage_mode`: `internal_research`
- Reddit should not require manual per-run enabling after collector implementation.

## Guardrails

- Do not store usernames by default.
- Do not store bulk thread dumps by default.
- Do not distribute Reddit-derived data to third parties.
- Do not train models on Reddit content.
- Require separate review before external/commercial productization.
- Require `source_url` plus relevant excerpt or summary.
- Allow selected context, but not full-thread archiving by default.
- Scale Reddit by measured yield; do not reduce signal quality for abstract caution alone.

## Validation Evidence

- `$env:PYTHONPATH="src"; .\.venv\Scripts\python.exe -m unittest tests.test_source_registry_query_planner -v`
  - Result: pass - ran 19 tests, OK
- `$env:PYTHONPATH="src"; .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v`
  - Result: pass - ran 317 tests, OK
- `.\scripts\oos-validate.ps1`
  - Result: pass - OOS validation complete
- `.\scripts\verify.ps1`
  - Result: pass - Verification complete
- `git diff --check`
  - Result: pass - no whitespace errors

## Roadmap State

- Current item unchanged.
- Completed count unchanged.
- Remaining count unchanged.
- This is a policy/architecture amendment only.

## Safety

- No push performed.
- No merge performed.
- No tag created.
- No release created.
- No internet/API calls made.
- No live LLM/API calls made.
