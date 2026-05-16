# Controlled Weekly Run Smoke Test — Runbook

**Roadmap:** v2.7 item 5.1 / v2.10 item 3.1-C
**Version:** 1.2
**Last updated:** 2026-05-16 (v2.14-FIX hardened gates)

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

## 9. Undo-Last Correction (v2.10)

```powershell
# Undo the most recent correction (replace or amend)
.\\.venv\\Scripts\\python.exe -m oos.cli import-founder-decisions-v2 `
  --project-root . `
  --run-id $run_id `
  --undo-last
```

**Expected output (if a correction exists to undo):**
- `Undo-last correction: OK`
- Lists undone correction details (correction_id, correction_mode, corrected_at)
- Lists restored decision IDs and removed decision IDs
- If undoing a replace: `Derived artifacts rebuilt:` lists rebuilt artifacts
- If undoing an amend: `Derived artifacts: No rebuild needed`
- `Source URL traceability: OK (placeholder_count=0, missing_count=0)`
- `Undo complete. A new undo entry has been appended to import_history.json.`
- Exit code 0

**Expected output (if no correction to undo):**
- Skips with no error (in the automated smoke script)
- In manual mode: `Undo-last correction: FAIL` with explanation

**After undo, verify source URL traceability:**
```powershell
.\\.venv\\Scripts\\python.exe -c "
import sys
sys.path.insert(0, 'src')
from oos.source_url_traceability import check_source_url_traceability
report = check_source_url_traceability('artifacts/weekly_runs/$run_id')
print(f'Placeholder URNs: {report.placeholder_url_count}')
print(f'Missing source URLs: {report.missing_source_url_count}')
print(f'Validation passed: {report.validation_passed}')
assert report.placeholder_url_count == 0, 'FAIL: Placeholder URNs found!'
assert report.missing_source_url_count == 0, 'FAIL: Missing source URLs!'
assert report.validation_passed, 'FAIL: Traceability validation failed!'
print('PASS: Post-undo source URL traceability clean.')
"
```

**If the undo fails:**
- Check that `import_history.json` exists and has at least one non-undo entry
- Check that `replaced_decisions/` or `amended_decisions/` archive exists and is valid
- Running `--undo-last` twice consecutively is rejected with "already undone"

## 10. Status Check

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

## 11. Run Report

```powershell
.\.venv\Scripts\python.exe -m oos.cli build-weekly-run-report-v2 `
  --project-root . `
  --run-id $run_id
```

**Expected:**
- `run_report.json` created in run directory
- `run_report.md` created in run directory
- Exit code 0

## 12. Dashboard

```powershell
.\.venv\Scripts\python.exe -m oos.cli weekly-dashboard-v2 `
  --project-root .
```

**Expected:**
- `artifacts/dashboard_index.json` created/updated
- `artifacts/dashboard.md` created/updated
- Exit code 0

## 13. Source URL Traceability Verification

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

## 14. Expected Artifacts

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

## 15. Expected Success Criteria

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

## 16. Expected Failure Modes

| Failure | Likely Cause | Fix |
|---------|-------------|-----|
| `run-weekly-cycle-v2` fails | Missing fixture file, bad PYTHONPATH | Check file exists, set `$env:PYTHONPATH="src"` |
| `import-founder-decisions-v2` fails | review_item_id mismatch | Regenerate decisions from actual inbox index IDs |
| `check_source_url_traceability` finds placeholders | Upstream regression in URL propagation | Investigate source URL chain; check items 1.1–1.3 |
| Artifacts missing | Pipeline step skipped or failed | Check the preceding steps passed |
| Dashboard shows zero runs | Run directory under wrong path | Verify `artifacts/weekly_runs/` structure |
| Permission errors | Temp directory ACL issues | Use a short temp path, avoid deep nesting |

## 17. Cleanup Guidance

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

## 18. Troubleshooting

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

## 19. Explicit Safety Note

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

## 20. Operational Discovery Pilot Smoke (v2.12 item 8)

### Purpose

This additional smoke step runs the full Operational Discovery Pilot pipeline end-to-end using deterministic fixture input and verifies all required pilot artifacts are produced correctly. It serves as the controlled smoke gate proving the pilot pipeline is operational before any live collection is attempted.

### What It Verifies

- **Pipeline integrity:** The pilot orchestrator (`run_operational_discovery_pilot()`) runs successfully from raw evidence through founder review package.
- **Artifact completeness:** All 9 required artifacts exist under the temp output directory.
- **Source scope:** Only `hacker_news` and `github_issues` are used; no deferred sources (Product Hunt, Reddit, Discord, etc.) appear.
- **Source URL traceability:** Every raw evidence `source_url` is a real `http(s)://` URL; zero placeholder or `github://` URLs.
- **Validation summary:** The `validation_summary.json` reports `is_valid=True`.
- **Source Quality Report:** Exists and is structurally valid with `artifact_type=source_quality_report`.
- **Founder Review Package:** Exists with clean `traceability_status`.

### Expected Artifacts

The pilot smoke step verifies these files exist under `<temp_root>/pilot_output/pilot_smoke_v2_12/`:

| Artifact | Format | Verification |
|----------|--------|-------------|
| `raw_evidence.json` | JSON | Exists, all source_urls are http(s) |
| `candidate_signals.json` | JSON | Exists, count >= 1 |
| `pain_clusters.json` | JSON | Exists, count >= 1 |
| `source_quality_report.json` | JSON | Exists, artifact_type correct |
| `source_quality_report.md` | Markdown | Exists |
| `founder_review_package.json` | JSON | Exists, traceability_status=clean |
| `founder_review_package.md` | Markdown | Exists |
| `validation_summary.json` | JSON | Exists, is_valid=True |
| `pilot_run_manifest.json` | JSON | Exists |

Optional artifacts (`opportunity_candidates.json`, `duplicates.json`) may also appear but are not required.

### No Live APIs / No LLMs

The pilot smoke step uses deterministic in-memory fixture data only:
- No network calls to HN Algolia API or GitHub API.
- No LLM calls to OpenAI, Anthropic, or any other provider.
- No source collector calls.
- No deferred sources.

### Temp-Output Behavior

All pilot artifacts are written to a temp directory under `$TempRoot/pilot_output/`. The real repository `artifacts/` directory is never touched. The `discovery_run_id` is fixed to `pilot_smoke_v2_12` for determinism.

### Failure Guidance

| Failure | Likely Cause | Fix |
|---------|-------------|-----|
| Source scope failure | Deferred source_id in fixture or pipeline | Verify fixture uses only `hacker_news` and `github_issues` |
| Traceability failure | Missing or non-http(s) source_url | Check fixture evidence has valid source_urls |
| Missing artifact | Pipeline phase failed or file not written | Check `run_operational_discovery_pilot` returns valid result |
| Invalid founder_review_package | traceability_status not clean | Check evidence source_urls are valid http(s) URLs |
| Invalid source_quality_report | artifact_type mismatch or missing source_metrics | Check source_quality_report.py build function |
| No pain clusters | Evidence items too dissimilar for clustering | Add more related evidence items or verify clustering logic |
| Pipeline errors | Unknown source type, bad data format | Check fixture evidence matches expected schema |
| Exit code non-zero | Any check failed | Review the specific FAIL lines in smoke output |

### Running the Pilot Smoke Standalone

The pilot smoke runs as part of the full controlled smoke script:

```powershell
.\scripts\run-controlled-smoke.ps1
```

The pilot step appears as "Step 10: Operational Discovery Pilot Smoke" and reports individual PASS/FAIL for each verification gate.

---

## 21. v2.14 Controlled Quality Smoke (v2.14 Item 9) — HARDENED v2.14-FIX

### Purpose

This smoke step runs the full Operational Discovery Pilot pipeline on a curated v2.14 quality fixture that exercises all quality gates introduced in v2.14. **v2.14-FIX hardens the gates so they no longer pass vacuously.** The step reads SQR JSON values directly and requires non-trivial outcomes when the fixture includes noise/weak signals and quality flags.

### What It Verifies (Hardened)

- **Gate A — Source Quality Report:** `noise_signal_total > 0`, `weak_signal_total > 0`, `classification_health != "clean"`, `evidence_quality_status != "clean"`, `flagged_record_count > 0`, `contradiction_warnings` count > 0, at least one per-source warning, Markdown contains non-empty warning bullets (not just section headers).
- **Gate B — PainCluster Assembly:** Mixed anchors do not collapse into one catch-all; coherent trace items share EXACTLY ONE cluster (includes v214_gh_prov_001); no dead/nme titles; zero catch-all risk clusters.
- **Gate C — Founder Review Package:** Unchanged (Executive Summary, SNR, Per-Source, Quality Gate, Opportunity Hypotheses).
- **Gate D — Opportunity Synthesis:** At least 1 opportunity candidate synthesized; `not_a_solution_yet = true`, `created_by = deterministic_stub`, `evidence_links` preserved; at least one unknown-actor hypothesis with `unproven; validate actor` ICP.

### Fixture Composition (v2.14-FIX)

The v2.14 quality smoke fixture includes 11 evidence items (added unknown-actor pair):

| Evidence ID | Source | Character | Expected Classification |
|-------------|--------|-----------|------------------------|
| `v214_gh_stack_001` | GitHub Issues | Concrete stack-trace debugging pain | Accepted |
| `v214_gh_trace_001` | GitHub Issues | Prompt replay / trace debugging pain | Accepted |
| `v214_gh_prov_001` | GitHub Issues | Multi-agent provenance pain (same topic_id) | Accepted |
| `v214_hn_noise_001` | HN | Product launch + vendor_promo flags | Noise |
| `v214_hn_noise_002` | HN | Product launch + launch_hype flags | Noise |
| `v214_hn_flagged_001` | HN | Evidence-only flags (low_text_context) | Weak/Noise |
| `v214_hn_pain_001` | HN | Positive pain flags (cost_signal, workaround) | Accepted (flagged) |
| `v214_hn_clean_001` | HN | Clean agent debugging pain (no flags) | Accepted |
| `v214_hn_unknown_001` | HN | Unknown actor agent debugging pain | Accepted |
| `v214_gh_unknown_001` | GitHub Issues | Unknown actor agent debugging pain | Accepted |

The unknown-actor pair has `target_user = "unknown"` in raw_metadata and `topic_id = "unknown_actor_debugging"`. This ensures at least one cluster exercises the unknown actor → `unproven; validate actor` path and produces a PROMOTE or NEEDS_MORE_EVIDENCE review item eligible for opportunity synthesis.

### Expected Artifacts

The v2.14 quality smoke writes only to `<temp_root>/v2_14_quality_smoke/pilot_smoke_v2_14_quality/`. All required artifacts are verified.

### Running the Quality Smoke Standalone

```powershell
.\scripts\run-controlled-smoke.ps1
```

The quality smoke step appears as "Step 11: v2.14 Controlled Quality Smoke" and reports individual PASS/FAIL for each hardened gate check.

### Smoke Assertions (HARDENED v2.14-FIX)

| Gate | Assertion | Expected |
|------|-----------|----------|
| A1 | noise_signal_total | > 0 (from SQR JSON, not Markdown) |
| A2 | weak_signal_total | > 0 (from SQR JSON) |
| A3 | classification_health | != `clean` (mandatory when noise/weak/flags exist) |
| A4 | evidence_quality_status | != `clean` |
| A5 | flagged_record_count | > 0 |
| A6 | dominant_quality_flags | Includes vendor_promo/suspected_self_promo/low_confidence_source/requires_manual_review |
| A7 | contradiction_warnings | len(cw) > 0 (not just isinstance check) |
| A8 | Per-source warnings | At least one source has non-empty warnings |
| A9 | Markdown warning bullets | Non-empty bullet content, not only section headers |
| B1 | Multiple clusters | > 1 cluster (not single catch-all) |
| B2 | Coherent trace items | EXACTLY 1 cluster (not ≤ 2); includes v214_gh_prov_001 |
| B3 | No dead/nme titles | Zero `[dead]` or `needs_more_evidence` titles |
| B4 | Zero catch-all risk | No `catch_all_risk = true` clusters |
| C1–C5 | FRP sections | Unchanged |
| D1 | Opportunity candidates count | >= 1 (not "may be empty") |
| D2 | not_a_solution_yet | True on all hypotheses |
| D3 | created_by | `deterministic_stub` on all hypotheses |
| D4 | evidence_links | Non-empty on all hypotheses |
| D5 | Unknown actor hypothesis | At least one hypothesis exercises unknown actor |
| D6 | No invented ICP | Unknown actor → `unproven; validate actor` |

### Previous 0-Opportunity Gap Fixed

Prior to v2.14-FIX, gates D1–D5 passed vacuously when `opportunity_candidate_count = 0`. The fixture now includes an unknown-actor evidence pair (`v214_hn_unknown_001`, `v214_gh_unknown_001`) with clean pain signals from two sources, which enables a cluster with PROMOTE or NEEDS_MORE_EVIDENCE recommendation eligible for deterministic opportunity synthesis. Additionally, `v214_gh_prov_001` was moved from `topic_id = "agent_provenance"` to `"agent_debugging_traces"` so three clean GitHub items cohere into one eligible cluster.

### Failure Guidance

| Failure | Likely Cause | Fix |
|---------|-------------|-----|
| Gate A1/A2/A3/A4 fail | Noise classifier not rejecting flagged evidence | Check `noise_classifier.py` rules for vendor_promo, low_text_context |
| Gate A7 fail | SQR contradiction detection not triggered | Check `source_quality_report.py` contradiction thresholds |
| Gate A8 fail | Per-source warnings empty | Check per_source_warnings population in SQR |
| Gate A9 fail | Markdown renders headers without warning bullets | Check `render_source_quality_report_markdown` outputs bullet lines |
| Gate B1 fail | Catch-all cluster formed | Check cluster assembly `_should_merge()` and canonical anchors |
| Gate B2 fail | Coherent items split across > 1 cluster | Check cluster assembly for topic_id co-location |
| Gate B3 fail | Bad cluster title generated | Check `generate_cluster_review_title()` fallback logic |
| Gate D1 fail | Zero candidates synthesized | Check eligibility gates in `_cluster_is_eligible()` |
| Gate D5/D6 fail | Unknown actor path broken | Check `target_icp` assignment in `synthesize_opportunities()` |

### No Live APIs / No LLMs

The v2.14 quality smoke step uses deterministic in-memory fixture data only. No network calls. No LLM calls. All assertions are computed from pipeline outputs.

### Temp-Output Behavior

All v2.14 quality smoke artifacts are written to a temp directory under `$TempRoot/v2_14_quality_smoke/`. The real repository `artifacts/` directory is never touched.

---

**For automated execution, use the companion script:**

```powershell
.\scripts\run-controlled-smoke.ps1
```

This script executes all steps in a temporary project root, verifies outputs, and reports PASS/FAIL without touching the real repository.
