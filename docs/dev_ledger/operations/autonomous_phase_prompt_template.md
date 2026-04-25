# Autonomous Phase Prompt Template

Use this prompt when asking Codex to execute an approved phase autonomously.

```text
Implement autonomous phase: {{phase_name}}.

Source of truth:
- {{source_of_truth}}
- docs/dev_ledger/

Roadmap items included:
- {{roadmap_items_included}}

Branch/workflow mode:
- {{branch_workflow_mode}}
- Work one roadmap item at a time.
- Validate each item.
- Update roadmap only after validation passes.
- Update Dev Ledger only after validation passes.
- Create one local commit after each green mini-epic.
- Do not push.
- Do not merge.

Stop conditions:
- {{stop_conditions}}
- Stop only on critical blockers described in docs/dev_ledger/operations/stop_conditions.md.

Validation commands:
- {{validation_commands}}
- Always include focused tests, full unittest discovery, and .\scripts\verify.ps1.

Commit policy:
- {{commit_policy}}
- No git add .
- Targeted staging only.
- Do not commit temp files, .test-tmp, or .tmp_tests.

Execution rules:
- Do not implement future roadmap items early.
- Do not add live LLM/API calls unless explicitly in scope.
- Do not add external dependencies unless explicitly approved.
- Preserve Windows-native workflow.
- Report files changed, validation results, roadmap updates, Dev Ledger updates, and local commit status after each item.
```

