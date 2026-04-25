# Commit Policy

## Local Commits

- Create one local commit after each completed green mini-epic.
- Commit only after focused tests, full tests, and `.\scripts\verify.ps1` pass.
- Use clear commit messages that name the mini-epic or support item.

## Staging Rules

- Do not use `git add .`.
- Use targeted `git add` for exact files changed by the mini-epic.
- Review `git status --short` before committing.

## Files Never To Commit

- `.env`
- secrets or credentials
- `.venv`
- generated `artifacts/` unless explicitly requested
- `.test-tmp/`
- `.tmp_tests/`
- local temp files

## Push Policy

- Do not push unless explicitly requested.
- Phase-level push / PR is allowed only after user approval.
- Do not merge unless explicitly requested.

