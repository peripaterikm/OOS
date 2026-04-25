# Permissions Policy

## Codex May Do Without Asking

- Read the active roadmap, README, Dev Ledger, tests, and source files.
- Edit code, docs, and tests within the approved roadmap or support scope.
- Create new `src/oos` modules when needed by the approved scope.
- Create focused tests and acceptance tests.
- Run PowerShell validation commands.
- Fix failing tests within the approved scope.
- Update the roadmap only after validation passes.
- Update the Dev Ledger only after validation passes.
- Create local git commits after validation passes.

## Codex Must Not Do Without Asking

- `git push`
- merge PRs or branches
- delete tracked files
- change roadmap scope or order
- add live LLM/API calls
- add external dependencies
- change Python, runtime, package manager, or tooling versions
- touch secrets, credentials, `.env`, tokens, or key files
- introduce UI, database, scheduler, daemon, or external service behavior unless explicitly in scope
- continue after repeated validation failure

## Commit Permission

Local commits are permitted only after green validation and targeted staging. Push remains blocked unless the user explicitly requests it.

