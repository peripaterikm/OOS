# Support B Autonomous Codex Workflow

## Goal

Create a documented autonomous workflow so Codex can execute approved roadmap scopes with local commits, validation, roadmap updates, and Dev Ledger updates while stopping only for critical blockers.

## Context

Roadmap v2.2 development now has repeated mini-epic patterns: implement narrow scope, validate, update roadmap, update Dev Ledger, and commit locally. This support mini-epic documents those rules so the workflow can become more autonomous without losing safety.

## Inputs

- Active Roadmap v2.2 checklist
- Dev Ledger v0
- Existing validation commands
- Local-first commit workflow
- Known Windows temp ACL constraints

## Outputs

- `docs/dev_ledger/operations/`
- Autonomous protocol, permissions, stop, commit, and validation policies
- Reusable autonomous phase prompt template
- `scripts/oos-validate.ps1`
- `scripts/oos-status.ps1`
- Structural tests for the autonomous workflow docs

## Key Decisions

- Autonomous work remains local-first.
- Codex may create local commits after green validation, but may not push or merge without explicit approval.
- Roadmap and Dev Ledger final-state updates remain validation-gated.
- Stop conditions are narrow and explicit.

## Alternatives Rejected

- Letting Codex push automatically.
- Letting Codex change roadmap order autonomously.
- Combining validation, push, and merge into one script.
- Changing product/application behavior as part of this support mini-epic.

## Validation

- `tests.test_autonomous_workflow_docs`
- Full unittest discovery
- `scripts/oos-validate.ps1`
- `scripts/verify.ps1`

## Known Limitations

- This is documentation and local workflow support only.
- It does not implement Roadmap item `5.2`.
- It does not remove known Windows temp ACL warnings.

## Next Step

Use the autonomous protocol for future approved Roadmap v2.2 phase execution.

