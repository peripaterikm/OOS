# Validation Policy

## Required Order

1. Run focused tests for the current mini-epic.
2. Run full unittest discovery:

   ```powershell
   $env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
   ```

3. Run:

   ```powershell
   .\scripts\verify.ps1
   ```

4. For convenience after support mini-epic B, run:

   ```powershell
   .\scripts\oos-validate.ps1
   ```

## Acceptance Tests

Roadmap items require acceptance tests that check:

- no live LLM/API calls unless explicitly in scope
- no premature `run-signal-batch` / orchestrator wiring unless explicitly in scope
- roadmap final state after validation
- preservation of key traceability and fallback rules

## Green Validation

Validation is green only when:

- focused tests pass
- full unittest discovery passes
- `.\scripts\verify.ps1` passes
- no acceptance-blocking warnings remain

Roadmap and Dev Ledger final-state updates happen only after validation passes.

