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

Open the founder package:

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
Get-ChildItem artifacts\weekly_reviews
Get-ChildItem artifacts\founder_reviews
Get-Content artifacts\ops\founder_review_inbox.md
```

The weekly review should include the recorded founder decision, the portfolio state should reflect the decision, and traceability should point back to the input `signal_id` values.
