# Controlled Weekly Run Smoke Test — Runbook

**Roadmap:** v2.7 item 5.1
**Version:** 1.0
**Last updated:** 2026-05-08

## 1. Purpose

This runbook defines a step-by-step procedure for executing a bounded, deterministic weekly cycle with fixture signals, reviewing the output, recording decisions, and verifying the full source URL traceability chain. It serves as the controlled real-run smoke test before any live collection is attempted.

Every step is copy-paste-able PowerShell. No live APIs, no live LLMs, no internet access, no portfolio auto-transitions.

## 2. Preconditions

- Windows 10/11 with PowerShell 5.1+
- Python 3.10+ virtual environment at `.venv/`
- Repository at the project root with all dependencies installed
- Working tree is clean: `git status --short` shows no unexpected changes
- Branch is `feat/v2-7-traceability-block-1` (or equivalent feature branch)

## 3. Safety Boundaries

**This runbook NEVER:**
- Calls live APIs or LLM providers
- Accesses the internet
- Writes to real `artifacts/` directory (uses temp directories)
- Runs `git add`, `git commit`, `git push`, `git merge`, `git tag`, `git reset`, `git clean`
- Runs `gh pr create` or `gh pr merge`
- Deletes branches or files outside temp directories
- Makes autonomous portfolio decisions
- Promotes or kills opportunities automatically

**All pipeline runs happen in temporary directories.** The real repository `artifacts/` directory is never touched.

## 4. Pre-flight Checks

```powershell
# Confirm branch
git branch --show-current

# Confirm clean working tree
git status --short

# Confirm venv exists
Test-Path .\.venv\Scripts\python.exe

# Run developer validation
.\scripts\dev-validate-final.ps1 -SkipFullTests -SkipOOSValidate

# Run git diff check
git diff --check
```

All checks must pass before proceeding.

## 5. Fixture Input Setup

The smoke test uses the v2.5 evaluation dataset fixture at:
`examples/evaluation_dataset_v2_5/opportunity_quality_cases_v1.json`

This fixture contains 10 labeled opportunity quality cases with embedded evidence packs, source URLs, and expected gate decisions. It exercises the full pipeline deterministically.

For manual step-by-step execution, the fixture signals are used directly by the pipeline. For automated execution, use:

```powershell
.\scripts\run-controlled-smoke.ps1
```

## 6. Weekly Cycle Run

```powershell
# Set up Python path
$env:PYTHONPATH = "src"

# Run the weekly cycle with fixture input
.\.venv\Scripts\python.exe -m oos.cli run-weekly-cycle-v2 `
  --project-root . `
  --input-file examples\evaluation_dataset_v2_5\opportunity_quality_cases_v1.json
```

**Expected output:**
- Prints run_id, run_dir, artifact_count, validation_passed=True
- Exit code 0
- Artifacts written under `artifacts/weekly_runs/{run_id}/`

**If this fails:**
- Check that `$env:PYTHONPATH` is set to `src`
- Check that the fixture file exists
- Check that `.venv` is active and dependencies are installed
- See Troubleshooting section below

## 7. Founder Inbox Review

```powershell
# Find the latest run_id
$run_id = (Get-ChildItem artifacts\weekly_runs | Sort-Object Name -Descending | Select-Object -First 1).Name
Write-Host "Latest run: $run_id"

# Open the Markdown inbox
notepad "artifacts\weekly_runs\$run_id\founder_inbox_v2.md"

# Inspect the machine-readable index
.\.venv\Scripts\python.exe -c "
import json
with open('artifacts/weekly_runs/$run_id/founder_inbox_v2_index.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(f'Review items: {len(data.get(\"review_items\", []))}')
print(f'Sections: {len(data.get(\"sections\", []))}')
"
```

**Expected:**
- `founder_inbox_v2.md` exists and is populated
- `founder_inbox_v2_index.json` exists and is valid JSON
- Review items have `linked_source_urls` populated (non-empty for items with evidence lineage)
- No `urn:oos:*` placeholder URNs in any `linked_source_urls`

## 8. Decision Import

```powershell
# Create a temporary decisions file for fixture-based decisions
# (The E2E validation runner auto-generates this; for manual execution,
#  create a minimal decisions JSON file)

# Example minimal decisions file
$decisions_json = @"
[
  {
    "review_item_id": "review_item_001",
    "decision": "PROMOTE",
    "reason_category": "strong_signal_with_clear_icp_match",
    "founder_note": "Smoke test decision"
  }
]
"@

# NOTE: Replace review_item_id with an actual ID from founder_inbox_v2_index.json
# For the automated smoke script, this is handled automatically.
```

```powershell
# Import decisions
.\.venv\Scripts\python.exe -m oos.cli import-founder-decisions-v2 `
  --project-root . `
  --run-id $run_id `
  --decisions-file path\to\fixture_decisions.json
```

**Expected output:**
- Imported N decisions
- Exit code 0
- Artifacts updated in run directory

## 9. Status Check

```powershell
.\.venv\Scripts\python.exe -m oos.cli weekly-cycle-status-v2 `
  --project-root . `
  --run-id $run_id
```

**Expected output:**
- Structured status report with artifact presence/absence
- Decision count, feedback mapping count
- Advisory-only and safety flags confirmed
- Exit code 0

## 10. Run Report

```powershell
.\.venv\Scripts\python.exe -m oos.cli build-weekly-run-report-v2 `
  --project-root . `
  --run-id $run_id
```

**Expected:**
- `run_report.json` created in run directory
- `run_report.md` created in run directory
- Exit code 0

## 11. Dashboard

```powershell
.\.venv\Scripts\python.exe -m oos.cli weekly-dashboard-v2 `
  --project-root .
```

**Expected:**
- `artifacts/dashboard_index.json` created/updated
- `artifacts/dashboard.md` created/updated
- Exit code 0

## 12. Source URL Traceability Verification

```powershell
.\.venv\Scripts\python.exe -c "
import sys
sys.path.insert(0, 'src')
from oos.source_url_traceability import check_source_url_traceability

report = check_source_url_traceability('artifacts/weekly_runs/$run_id')
print(f'Placeholder URNs: {report.placeholder_url_count}')
print(f'Missing source URLs: {report.missing_source_url_count}')
print(f'Malformed URLs: {report.malformed_url_count}')
print(f'Artifacts checked: {report.artifacts_checked}')
print(f'Validation passed: {report.validation_passed}')

if report.placeholder_url_count > 0:
    print('FAIL: Placeholder URNs found!')
    for issue in report.issues:
        if issue.issue_type == 'placeholder_source_url':
            print(f'  {issue.artifact_key}: {issue.source_url_value}')
    sys.exit(1)
else:
    print('PASS: Zero placeholder URNs.')
    sys.exit(0)
"
```

**Expected:**
- `placeholder_url_count: 0`
- `validation_passed: True`
- Exit code 0

## 13. Expected Artifacts

After a successful smoke test, the following artifacts should exist under `artifacts/weekly_runs/{run_id}/`:

| Artifact | Format | Expected |
|----------|--------|----------|
| `manifest.json` | JSON | Present, valid, advisory_only=true, no_live_api=true, no_live_llm=true |
| `evidence_packs.json` | JSON | Present, items with source_urls |
| `opportunity_candidates.json` | JSON | Present |
| `quality_gate_decisions.json` | JSON | Present |
| `founder_decisions_v2.json` | JSON | Present after decision import |
| `founder_feedback_mappings.json` | JSON | Present after decision import |
| `founder_preference_profile.json` | JSON | Present after decision import |
| `weekly_opportunity_review.json` | JSON | Present |
| `next_best_actions.json` | JSON | Present |
| `parking_lot_records.json` | JSON | Present |
| `run_report.json` | JSON | Present after run report build |
| `founder_inbox_v2_index.json` | JSON | Present |
| `founder_inbox_v2.md` | Markdown | Present, populated |
| `run_report.md` | Markdown | Present after run report build |

Cross-run artifacts:
| Artifact | Format | Expected |
|----------|--------|----------|
| `artifacts/dashboard_index.json` | JSON | Present after dashboard build |
| `artifacts/dashboard.md` | Markdown | Present after dashboard build |

## 14. Expected Success Criteria

1. **Pipeline completeness:** All 14 run artifacts and 2 dashboard artifacts exist.
2. **Founder inbox populated:** `founder_inbox_v2.md` and `founder_inbox_v2_index.json` exist with review items.
3. **Decisions importable:** Founder decisions import without errors.
4. **Status valid:** `weekly-cycle-status-v2` reports valid state.
5. **Reports generated:** Run report JSON/MD and dashboard JSON/MD created.
6. **Zero placeholder URNs:** Source URL traceability check finds zero `urn:oos:*` placeholders.
7. **Real source URLs present:** Key artifacts carry non-empty `source_urls` or `linked_source_urls`.
8. **Advisory-only:** No autonomous portfolio decisions made.
9. **Deterministic:** Re-running with same fixture produces same run_id.
10. **No live calls:** No API or LLM calls made.

## 15. Expected Failure Modes

| Failure | Likely Cause | Fix |
|---------|-------------|-----|
| `run-weekly-cycle-v2` fails | Missing fixture file, bad PYTHONPATH | Check file exists, set `$env:PYTHONPATH="src"` |
| `import-founder-decisions-v2` fails | review_item_id mismatch | Regenerate decisions from actual inbox index IDs |
| `check_source_url_traceability` finds placeholders | Upstream regression in URL propagation | Investigate source URL chain; check items 1.1–1.3 |
| Artifacts missing | Pipeline step skipped or failed | Check the preceding steps passed |
| Dashboard shows zero runs | Run directory under wrong path | Verify `artifacts/weekly_runs/` structure |
| Permission errors | Temp directory ACL issues | Use a short temp path, avoid deep nesting |

## 16. Cleanup Guidance

**For manual runs using real `artifacts/`:**

```powershell
# List weekly runs
Get-ChildItem artifacts\weekly_runs

# Remove a specific run (replace with actual run_id)
# Remove-Item -Recurse -Force "artifacts\weekly_runs\weekly_run_2026-05-08_abc123def456"

# Remove dashboard index to force rebuild
# Remove-Item artifacts\dashboard_index.json
# Remove-Item artifacts\dashboard.md
```

**For automated smoke tests:** The smoke script uses temporary directories that are cleaned up automatically by the OS. No manual cleanup needed.

**Important:**
- Never delete `artifacts/` directory itself — only specific run subdirectories.
- Never delete `.git/`, `src/`, `tests/`, `docs/`, `scripts/`, `config/`, or `examples/`.
- Never delete `.venv/` or `.gitignore`.

## 17. Troubleshooting

### Python module not found

```powershell
# Verify PYTHONPATH
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -c "import oos; print(oos.__file__)"
```

### CLI command not recognized

```powershell
# List available CLI commands
.\.venv\Scripts\python.exe -m oos.cli --help
```

### Permission denied writing artifacts

```powershell
# Check artifacts directory permissions
Get-Acl artifacts\

# Try running as administrator or use a different project root
```

### Deterministic run_id mismatch

The run_id is derived from `sha256(input_file_content + run_date.isoformat())[:12]`. If input file or date changes, the run_id changes. This is expected and correct.

### Venv not found or broken

```powershell
# Recreate venv
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 18. Explicit Safety Note

**This runbook does NOT perform:**

- `git push` — no remote updates
- `git merge` — no branch merging
- `git tag` — no release tags
- `gh pr create` or `gh pr merge` — no pull requests
- Live API calls — no `Invoke-RestMethod`, `Invoke-WebRequest`, `curl`, or `wget`
- Live LLM calls — no OpenAI, Anthropic, or other provider calls
- Portfolio auto-transitions — no autonomous promote/park/kill
- Deletion of tracked files — no `git clean`, `git reset --hard`, `Remove-Item` on tracked paths
- Writing to `artifacts/` in automated mode — smoke script uses temp directories

**For automated execution, use the companion script:**

```powershell
.\scripts\run-controlled-smoke.ps1
```

This script executes all steps in a temporary project root, verifies outputs, and reports PASS/FAIL without touching the real repository.
