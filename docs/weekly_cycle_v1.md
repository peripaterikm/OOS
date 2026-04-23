# Weekly Cycle v1

This runbook is the Windows-native path for one real OOS weekly cycle.

## Input File

Use the canonical JSONL signal batch format:

```powershell
examples\real_signal_batch.jsonl
```

Each line is one JSON object with `signal_id`, `captured_at`, `source_type`, `title`, `text`, and `source_ref`.

## Run Weekly Cycle

Run the real weekly cycle against a clean project root:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m oos.cli run-weekly-cycle --project-root . --input-file examples\real_signal_batch.jsonl
```

The command writes runtime artifacts under `artifacts\`.

## Founder Review Step

Check the weekly cycle status:

```powershell
.\.venv\Scripts\python.exe -m oos.cli weekly-cycle-status --project-root .
```

Open the founder package if you want the full markdown inbox:

```powershell
notepad artifacts\ops\founder_review_inbox.md
```

The machine-readable index is written to `artifacts\ops\founder_review_index.json`.

## Decision Recording Step

Record a founder decision by review ID:

```powershell
.\.venv\Scripts\python.exe -m oos.cli record-founder-review --project-root . --review-id review-001 --decision pass
```

Use `pass`, `park`, or `kill` according to the review inbox.

## Output Check Step

Check the updated artifacts:

```powershell
.\.venv\Scripts\python.exe -m oos.cli weekly-cycle-status --project-root .
Get-ChildItem artifacts\weekly_reviews
Get-ChildItem artifacts\founder_reviews
```

The status command should show available `review_id` values before the decision, then show the recorded founder decision, updated weekly review path, portfolio/result summary, and traceability back to the input `signal_id` values after the decision.
