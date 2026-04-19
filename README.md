# Opportunity Operating System (OOS) — v1 Core

This repository implements the v1 core of the Opportunity Operating System (OOS),
following the documentation in `docs/vision.md`, `docs/scope-v1.md`, and
`docs/build-order.md`.

Week 1 focuses on:

- project structure,
- configuration conventions,
- artifact directories,
- a basic CLI entrypoint,
- a lightweight orchestrator skeleton,
- a smoke-test command that writes dummy artifacts.

## Quick start (Week 1)

Assuming you are in the project root:

```bash
python -m venv .venv
.venv\Scripts\activate  # on Windows PowerShell
pip install -e .
oos smoke-test
```

The smoke test runs an empty pipeline via the orchestrator and writes a
dummy artifact into the `artifacts/smoke` directory.

