# Validation Policy

## Purpose

Validation evidence must live in files, not in manual PowerShell copy/paste. Every roadmap item must record what was run, where it was run, what passed or failed, and where fuller logs can be found when output is too long for the mini-epic record.

Manual validation is a fallback only. Codex should run validation and write/summarize evidence itself unless blocked by usage limits, approval limits, local ACL issues, or missing permissions.

## Canonical Run Report Path

Every roadmap item should write a validation report at:

```text
docs/dev_ledger/03_run_reports/<roadmap-item-slug>-validation.md
```

Example:

```text
docs/dev_ledger/03_run_reports/1.2-run-report-validation-standardization.md
```

## Required Validation Order

1. Run focused tests when applicable.
2. Run full unittest discovery:

   ```powershell
   $env:PYTHONPATH="src"; .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
   ```

3. Run project validation:

   ```powershell
   .\scripts\oos-validate.ps1
   ```

4. Run final verification:

   ```powershell
   .\scripts\verify.ps1
   ```

5. Run whitespace/diff validation:

   ```powershell
   git diff --check
   ```

## Required Evidence Fields

Each run report must include:

- roadmap item;
- branch;
- commit or pre-commit state;
- working directory;
- command;
- timestamp when practical;
- result: `pass`, `fail`, or `blocked`;
- short summary;
- location of full log if a separate log file exists;
- known warnings;
- blocked commands, if any;
- no push / no merge / no tag / no release confirmation.

## Blocked Validation

If Codex environment usage limits, approval limits, sandbox restrictions, or local Windows ACL issues block validation:

- record the attempted command;
- record the reason it was blocked;
- do not invent success;
- stop unless recent valid evidence exists and the roadmap item explicitly allows relying on that evidence.

If validation must be rerun outside the sandbox because of the documented Windows `TemporaryDirectory` ACL issue, the run report must say so.

## Acceptance Tests

Roadmap items require acceptance tests when behavior is implemented. Acceptance tests should check:

- no live LLM/API calls unless explicitly in scope;
- no premature runtime/orchestrator wiring unless explicitly in scope;
- progress-tolerant roadmap state checks;
- preservation of key traceability and fallback rules.

Documentation-only items may use focused structural tests instead of behavior tests.

## Green Validation

Validation is green only when:

- focused tests pass when applicable;
- full unittest discovery passes;
- `.\scripts\oos-validate.ps1` passes;
- `.\scripts\verify.ps1` passes;
- `git diff --check` passes;
- no acceptance-blocking warnings remain.

Roadmap and Dev Ledger final-state updates happen only after validation passes.
