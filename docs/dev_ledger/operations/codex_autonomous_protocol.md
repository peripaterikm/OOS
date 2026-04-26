# Codex Autonomous Protocol

## Purpose

Autonomous mode lets Codex execute approved roadmap scopes with less manual orchestration while preserving validation, traceability, local commits, roadmap state, and Dev Ledger state.

## Source Of Truth

- Active roadmap: `docs/roadmaps/OOS_roadmap_v2_3_source_intelligence_checklist.md`
- Development ledger: `docs/dev_ledger/`
- Current project state: `docs/dev_ledger/00_project_state.md`
- Operational policies: `docs/dev_ledger/operations/`
- Tests: `tests/`
- README: `README.md`

Archived roadmap files are reference-only unless the user explicitly says otherwise.

## Local-First Workflow

1. Read the active roadmap item and Dev Ledger context.
2. Implement exactly one approved mini-epic at a time.
3. Add or update focused tests and acceptance tests when behavior changes.
4. Run focused tests when applicable, full unittest discovery, `.\scripts\oos-validate.ps1`, `.\scripts\verify.ps1`, and `git diff --check`.
5. Write or update the item run report in `docs/dev_ledger/03_run_reports/`.
6. Update the roadmap only after validation passes.
7. Update the Dev Ledger after each completed mini-epic.
8. Create one local commit per completed green mini-epic.
9. Proceed to the next approved item unless a stop condition is met.

## Run Reports

Codex should write run reports itself. Codex should not ask the user to manually run validation unless blocked by a stop condition, usage/approval limit, missing local permission, or a known local ACL issue that cannot be worked around.

Run reports should summarize validation outputs and link to full logs when output is stored separately. They must include commands run, working directory, pass/fail/blocked result, known warnings, and confirmation that no push, merge, tag, release, or live LLM/API call occurred unless explicitly authorized.

## Git Rules

- One local commit per completed mini-epic after green validation.
- No push unless explicitly requested.
- No merge unless explicitly requested.
- No tag or release unless explicitly requested.
- No `git add .`; use targeted staging only.

Codex can push/open a PR only when explicitly authorized by the user; this is not part of normal item implementation.

## Validation Rules

Every completed roadmap item requires:

- focused tests for the new scope when applicable;
- acceptance tests for roadmap item behavior and no premature wiring when behavior changes;
- full unittest discovery;
- `.\scripts\oos-validate.ps1`;
- `.\scripts\verify.ps1`;
- `git diff --check`;
- file-based run report evidence.

Roadmap and Dev Ledger final-state updates happen only after validation passes.

## Stop Conditions

Stop and ask the user only when a condition in `stop_conditions.md` is met, such as conflicting acceptance criteria, a required new dependency, live API/secret need, repeated validation failure, or a destructive tracked-file operation.

## Reporting Format

After each completed item, report:

- files changed;
- validation commands and exact results;
- whether runtime/orchestrator behavior changed;
- whether live LLM/API calls were added;
- whether roadmap was updated;
- whether Dev Ledger was updated;
- local commit status;
- readiness for next item.
