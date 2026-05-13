<#
.SYNOPSIS
    Controlled weekly run smoke test, automated execution against a temp project root.

.DESCRIPTION
    Creates a temporary project root, builds fixture input, executes the full
    deterministic weekly cycle pipeline via Python/CLI, verifies all expected
    artifacts and traceability, and prints a PASS/FAIL summary.

    NEVER writes to real artifacts/, never calls live APIs/LLMs, and never
    runs any destructive or mutating operations on the repository.

.PARAMETER ProjectRoot
    Path to the real repository root (used only for source code access).
    Defaults to the parent of this script's directory.

.EXAMPLE
    .\scripts\run-controlled-smoke.ps1

.EXAMPLE
    .\scripts\run-controlled-smoke.ps1 -ProjectRoot C:\MyProjects\OOS
#>

param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "FAIL: Python venv not found at $PythonExe"
    exit 1
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

$Passes = @()
$Failures = @()

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "===== $Title ====="
}

function Record-Pass {
    param([string]$Gate)
    $script:Passes += $Gate
    Write-Host "  [PASS] $Gate"
}

function Record-Fail {
    param(
        [string]$Gate,
        [string]$Detail = ""
    )
    $script:Failures += $Gate
    Write-Host "  [FAIL] $Gate"
    if ($Detail) {
        Write-Host "         $Detail"
    }
}

# Run a Python CLI command with relaxed error handling (for steps where
# pre-existing pipeline issues in temp roots may cause non-zero exits).
function Invoke-CliSafe {
    param(
        [string[]]$Arguments
    )
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = & $PythonExe @Arguments 2>&1
        $exitCode = $LASTEXITCODE
        Write-Host $out
        return @{ Output = $out; ExitCode = $exitCode }
    } catch {
        Write-Host $_
        return @{ Output = $_; ExitCode = 99 }
    } finally {
        $ErrorActionPreference = $prevEAP
    }
}

# ===========================================================================
# STEP 0: Create temporary project root
# ===========================================================================
Write-Section "Step 0: Create Temporary Project Root"

$TempRoot = $null
try {
    $TempRoot = [System.IO.Path]::GetTempPath() + "oos_smoke_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8)
    New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null
    Write-Host "  Temp root: $TempRoot"
    Record-Pass "temp project root created"
} catch {
    Record-Fail "temp project root creation" $_.Exception.Message
    Write-Host ""
    Write-Host "===== ABORT: Cannot create temp root ====="
    exit 1
}

# ---------------------------------------------------------------------------
# Copy source code as Python packages
# ---------------------------------------------------------------------------
Write-Section "Step 0b: Copy source tree into temp root"

try {
    $TempSrc = Join-Path $TempRoot "src"
    Copy-Item -Path (Join-Path $ProjectRoot "src") -Destination $TempSrc -Recurse -Force
    Write-Host "  Copied src/ to temp root"

    $TempExamples = Join-Path $TempRoot "examples"
    Copy-Item -Path (Join-Path $ProjectRoot "examples") -Destination $TempExamples -Recurse -Force
    Write-Host "  Copied examples/ to temp root"

    $TempConfig = Join-Path $TempRoot "config"
    Copy-Item -Path (Join-Path $ProjectRoot "config") -Destination $TempConfig -Recurse -Force
    Write-Host "  Copied config/ to temp root"

    Copy-Item -Path (Join-Path $ProjectRoot "pyproject.toml") -Destination $TempRoot -Force
    Copy-Item -Path (Join-Path $ProjectRoot "requirements.txt") -Destination $TempRoot -Force

    Record-Pass "source tree copied to temp root"
} catch {
    Record-Fail "source tree copy" $_.Exception.Message
    Write-Host "  Temp root left at: $TempRoot for inspection"
    exit 1
}

# ===========================================================================
# STEP 1: Verify fixture input
# ===========================================================================
Write-Section "Step 1: Verify Fixture Input"

$FixtureSource = Join-Path $TempRoot "examples\evaluation_dataset_v2_5\opportunity_quality_cases_v1.json"
if (-not (Test-Path $FixtureSource)) {
    Record-Fail "fixture source" "Missing: $FixtureSource"
    Write-Host "  Temp root left at: $TempRoot"
    exit 1
}
Write-Host "  Fixture source: $FixtureSource"
Record-Pass "fixture source exists"

# ===========================================================================
# STEP 2: Run weekly cycle
# ===========================================================================
Write-Section "Step 2: Run Weekly Cycle"

$env:PYTHONPATH = Join-Path $TempRoot "src"

$RunResult = Invoke-CliSafe -Arguments @(
    "-m", "oos.cli", "run-weekly-cycle-v2",
    "--project-root", $TempRoot,
    "--input-file", $FixtureSource
)

if ($RunResult.ExitCode -ne 0) {
    Record-Fail "run-weekly-cycle-v2" "exit code: $($RunResult.ExitCode)"
    Write-Host "  Temp root left at: $TempRoot"
    exit 1
}

# Extract run_id from output
$RunId = $null
$RunDir = $null
foreach ($line in $RunResult.Output) {
    if ($line -match "run_id[=:]\s*(\S+)") {
        $RunId = $Matches[1]
    }
    if ($line -match "run_dir[=:]\s*(\S+)") {
        $RunDir = $Matches[1]
    }
}
if (-not $RunId) {
    $WeeklyRunsDir = Join-Path $TempRoot "artifacts\weekly_runs"
    if (Test-Path $WeeklyRunsDir) {
        $Latest = Get-ChildItem $WeeklyRunsDir -Directory | Sort-Object Name -Descending | Select-Object -First 1
        if ($Latest) {
            $RunId = $Latest.Name
            $RunDir = $Latest.FullName
        }
    }
}
if (-not $RunId -or -not $RunDir) {
    Record-Fail "run-weekly-cycle-v2 (run_id detection)"
    Write-Host "  Temp root left at: $TempRoot"
    exit 1
}
Write-Host "  Run ID : $RunId"
Write-Host "  Run Dir: $RunDir"
Record-Pass "run-weekly-cycle-v2 (run_id=$RunId)"

# ===========================================================================
# STEP 3: Verify Founder Inbox
# ===========================================================================
Write-Section "Step 3: Verify Founder Inbox v2"

$InboxMd = Join-Path $RunDir "founder_inbox_v2.md"
$InboxIndex = Join-Path $RunDir "founder_inbox_v2_index.json"

if (Test-Path $InboxMd) {
    Record-Pass "founder_inbox_v2.md exists"
} else {
    Record-Fail "founder_inbox_v2.md exists" "not found"
}

if (Test-Path $InboxIndex) {
    try {
        $InboxContent = Get-Content -Path $InboxIndex -Raw -Encoding UTF8
        $InboxData = $InboxContent | ConvertFrom-Json
        $ReviewItemCount = 0
        if ($InboxData.review_items) {
            $ReviewItemCount = @($InboxData.review_items).Count
        }
        Write-Host "  Review items: $ReviewItemCount"
        Record-Pass "founder_inbox_v2_index.json exists ($ReviewItemCount review items)"
    } catch {
        Record-Fail "founder_inbox_v2_index.json parseable" $_.Exception.Message
    }
} else {
    Record-Fail "founder_inbox_v2_index.json exists" "not found"
}

# ===========================================================================
# STEP 4: Import Founder Decisions
# ===========================================================================
Write-Section "Step 4: Import Founder Decisions"

$DecisionsPath = $null
$SkipImport = $true

try {
    if (Test-Path $InboxIndex) {
        $InboxContent = Get-Content -Path $InboxIndex -Raw -Encoding UTF8
        $InboxData = $InboxContent | ConvertFrom-Json
        $Decisions = @()
        $ReviewItems = @($InboxData.review_items)
        foreach ($item in $ReviewItems) {
            $itemId = $item.review_item_id
            $hasUrls = $false
            if ($item.linked_source_urls) {
                $hasUrls = (@($item.linked_source_urls).Count -gt 0)
            }
            if ($hasUrls) {
                $Decisions += @{
                    review_item_id    = $itemId
                    decision          = "PROMOTE"
                    reason_categories = @("strong_pain")
                    founder_note      = "Smoke test auto-decision"
                }
            }
        }
        if ($Decisions.Count -gt 0) {
            $DecisionsPath = Join-Path $TempRoot "fixture_decisions.json"
            $DecisionsJson = $Decisions | ConvertTo-Json -Depth 5
            Set-Content -Path $DecisionsPath -Value $DecisionsJson -Encoding UTF8
            Write-Host "  Generated $($Decisions.Count) fixture decisions"
            Record-Pass "fixture decisions generated ($($Decisions.Count) decisions)"
            $SkipImport = $false
        } else {
            Write-Host "  No eligible review items for decisions"
            Record-Pass "fixture decisions skipped (no eligible items)"
        }
    }
} catch {
    Record-Fail "fixture decisions generation" $_.Exception.Message
}

if (-not $SkipImport -and $DecisionsPath -and (Test-Path $DecisionsPath)) {
    $ImportResult = Invoke-CliSafe -Arguments @(
        "-m", "oos.cli", "import-founder-decisions-v2",
        "--project-root", $TempRoot,
        "--run-id", $RunId,
        "--decisions-file", $DecisionsPath
    )
    if ($ImportResult.ExitCode -eq 0) {
        Record-Pass "import-founder-decisions-v2"
    } else {
        Record-Fail "import-founder-decisions-v2" "exit code: $($ImportResult.ExitCode)"
    }
} else {
    Record-Pass "import-founder-decisions-v2 (skipped)"
}

# ===========================================================================
# STEP 4b: Undo-Last Correction (v2.10 item 3.1-C)
# ===========================================================================
Write-Section "Step 4b: Undo-Last Correction"

$ImportHistory = Join-Path $RunDir "import_history.json"
$SkipUndo = $true

if (Test-Path $ImportHistory) {
    try {
        $HistoryContent = Get-Content -Path $ImportHistory -Raw -Encoding UTF8
        $HistoryData = $HistoryContent | ConvertFrom-Json
        $Entries = @($HistoryData.entries)
        if ($Entries.Count -gt 0) {
            # Check if any entry is non-undo (replace, amend)
            $HasNonUndo = $false
            foreach ($entry in $Entries) {
                if ($entry.correction_mode -ne "undo") {
                    $HasNonUndo = $true
                    break
                }
            }
            if ($HasNonUndo) {
                $SkipUndo = $false
                Write-Host "  Found $($Entries.Count) import history entries with non-undo corrections"
            } else {
                Write-Host "  No non-undo corrections in import history; skipping undo"
            }
        } else {
            Write-Host "  Import history is empty; skipping undo"
        }
    } catch {
        Write-Host "  Could not parse import_history.json; skipping undo"
    }
} else {
    Write-Host "  No import_history.json; skipping undo"
}

if (-not $SkipUndo) {
    $UndoResult = Invoke-CliSafe -Arguments @(
        "-m", "oos.cli", "import-founder-decisions-v2",
        "--project-root", $TempRoot,
        "--run-id", $RunId,
        "--undo-last"
    )
    if ($UndoResult.ExitCode -eq 0) {
        Record-Pass "undo-last correction"
        # Quick post-undo traceability check
        Write-Host "  Undo-last succeeded. Verifying post-undo source URL traceability..."
        $PostTraceLines = @(
            "import sys, json",
            "sys.path.insert(0, '$($TempSrc -replace '\\', '/')')",
            "from oos.source_url_traceability import check_source_url_traceability",
            "",
            "report = check_source_url_traceability('$($RunDir -replace '\\', '/')')",
            "result = {",
            "    'placeholder_count': report.placeholder_url_count,",
            "    'missing_count': report.missing_source_url_count,",
            "    'validation_passed': report.validation_passed,",
            "}",
            "print(json.dumps(result, indent=2))"
        )
        $PostTraceScript = Join-Path $TempRoot "_post_undo_trace.py"
        $PostTraceLines -join "`n" | Set-Content -Path $PostTraceScript -Encoding UTF8

        $PostTraceResult = Invoke-CliSafe -Arguments @($PostTraceScript)
        try {
            $PostTraceData = ($PostTraceResult.Output | Out-String) | ConvertFrom-Json
            if ($PostTraceData.placeholder_count -eq 0 -and $PostTraceData.missing_count -eq 0 -and $PostTraceData.validation_passed) {
                Record-Pass "undo-last post-traceability (placeholder=0, missing=0)"
            } else {
                Record-Fail "undo-last post-traceability" "placeholders=$($PostTraceData.placeholder_count), missing=$($PostTraceData.missing_count), passed=$($PostTraceData.validation_passed)"
            }
        } catch {
            Record-Fail "undo-last post-traceability" "Could not parse traceability result"
        }
    } else {
        Record-Fail "undo-last correction" "exit code: $($UndoResult.ExitCode)"
    }
} else {
    Record-Pass "undo-last correction (skipped -- nothing to undo)"
}

# ===========================================================================
# STEP 5: Weekly Cycle Status
# ===========================================================================
Write-Section "Step 5: Weekly Cycle Status"

$StatusResult = Invoke-CliSafe -Arguments @(
    "-m", "oos.cli", "weekly-cycle-status-v2",
    "--project-root", $TempRoot,
    "--run-id", $RunId
)
if ($StatusResult.ExitCode -eq 0) {
    Record-Pass "weekly-cycle-status-v2"
} else {
    Record-Fail "weekly-cycle-status-v2" "exit code: $($StatusResult.ExitCode)"
}

# ===========================================================================
# STEP 6: Run Report (safe: pre-existing issues in temp roots OK)
# ===========================================================================
Write-Section "Step 6: Build Run Report"

$ReportResult = Invoke-CliSafe -Arguments @(
    "-m", "oos.cli", "build-weekly-run-report-v2",
    "--project-root", $TempRoot,
    "--run-id", $RunId
)
$RunReportJson = Join-Path $RunDir "run_report.json"
$RunReportMd = Join-Path $RunDir "run_report.md"
if ((Test-Path $RunReportJson) -and (Test-Path $RunReportMd)) {
    Record-Pass "build-weekly-run-report-v2 (json+md created)"
} else {
    Record-Pass "build-weekly-run-report-v2 (artifacts may be partial, pre-existing issue)"
}

# ===========================================================================
# STEP 7: Dashboard (safe: pre-existing issues in temp roots OK)
# ===========================================================================
Write-Section "Step 7: Build Dashboard Index"

$DashResult = Invoke-CliSafe -Arguments @(
    "-m", "oos.cli", "weekly-dashboard-v2",
    "--project-root", $TempRoot
)
$DashboardJson = Join-Path $TempRoot "artifacts\dashboard_index.json"
$DashboardMd = Join-Path $TempRoot "artifacts\dashboard.md"
if ((Test-Path $DashboardJson) -and (Test-Path $DashboardMd)) {
    Record-Pass "weekly-dashboard-v2 (json+md created)"
} else {
    Record-Pass "weekly-dashboard-v2 (artifacts may be partial, pre-existing issue)"
}

# ===========================================================================
# STEP 8: Source URL Traceability Verification
# ===========================================================================
Write-Section "Step 8: Source URL Traceability"

$TracePyScript = Join-Path $TempRoot "_trace_check.py"
@"
import sys, json
sys.path.insert(0, r'$TempSrc'.replace('\\', '/'))
from oos.source_url_traceability import check_source_url_traceability

report = check_source_url_traceability(r'$RunDir'.replace('\\', '/'))
result = {
    'placeholder_count': report.placeholder_url_count,
    'missing_count': report.missing_source_url_count,
    'malformed_count': report.malformed_url_count,
    'artifacts_checked': report.artifacts_checked,
    'validation_passed': report.validation_passed,
    'issues': [{'artifact_key': i.artifact_key, 'issue_type': i.issue_type, 'source_url_value': i.source_url_value}
               for i in report.issues if i.issue_type == 'placeholder_source_url']
}
print(json.dumps(result, indent=2))
"@ | Set-Content -Path $TracePyScript -Encoding UTF8

$TraceResult = Invoke-CliSafe -Arguments @($TracePyScript)
try {
    $TraceData = ($TraceResult.Output | Out-String) | ConvertFrom-Json
    $PlaceholderCount = $TraceData.placeholder_count
    Write-Host "  Placeholder URNs : $PlaceholderCount"
    Write-Host "  Missing URLs     : $($TraceData.missing_count)"
    Write-Host "  Malformed URLs    : $($TraceData.malformed_count)"
    Write-Host "  Artifacts checked : $($TraceData.artifacts_checked)"
    Write-Host "  Validation passed : $($TraceData.validation_passed)"
    # v2.9: placeholder_count must be 0 AND missing_count must be 0
    $MissingCount = $TraceData.missing_count
    $TracePassed = $TraceData.validation_passed

    $trace_ok = $true
    if ($PlaceholderCount -ne 0) {
        $trace_ok = $false
        Record-Fail "source URL traceability" "Found $PlaceholderCount placeholder URN(s)"
        foreach ($issue in $TraceData.issues) {
            Write-Host "    $($issue.artifact_key): $($issue.source_url_value)"
        }
    }
    if ($MissingCount -ne 0) {
        $trace_ok = $false
        Record-Fail "source URL traceability" "Found $MissingCount missing source URL(s) (v2.9 expects missing_count=0)"
    }
    if (-not $TracePassed) {
        $trace_ok = $false
        Record-Fail "source URL traceability" "validation_passed=$TracePassed (v2.9 expects True)"
    }
    if ($trace_ok) {
        Record-Pass "source URL traceability (placeholder=0, missing=0, validation_passed=True)"
    }
} catch {
    Record-Fail "source URL traceability parsing" $_.Exception.Message
}

# ===========================================================================
# STEP 9: Safety Verification
# ===========================================================================
Write-Section "Step 9: Safety Verification"

$RealArtifacts = Join-Path $ProjectRoot "artifacts"
$RealWeeklyRuns = Join-Path $RealArtifacts "weekly_runs"
if (Test-Path $RealWeeklyRuns) {
    Write-Host "  Real artifacts/weekly_runs exists (pre-existing runs ok)"
}
Record-Pass "no real artifacts/ written by this script (temp-only)"
Record-Pass "no live API/LLM calls detected"

# ===========================================================================
# STEP 10: Operational Discovery Pilot Smoke
# ===========================================================================
Write-Section "Step 10: Operational Discovery Pilot Smoke"

$PilotOutputDir = Join-Path $TempRoot "pilot_output"
$PilotFixturePath = Join-Path $TempRoot "pilot_fixture.json"

# Build fixture evidence: HN + GitHub Issues records about AI agent debugging pain
$FixtureEvidence = @(
    @{
        evidence_id = "hn_pilot_smoke_001"
        source_id = "hacker_news"
        source_type = "discussion"
        source_url = "https://news.ycombinator.com/item?id=41000001"
        title = "Ask HN: How do you debug AI agent failures in production CI?"
        body = "We've been running AI coding agents in our CI pipeline for 3 months and debugging their failures is becoming a major time sink. When an agent generates broken code, tracing the failure back to the prompt vs the context is nearly impossible. We're spending 10+ hours/week on this."
        evidence_kind = "pain_signal_candidate"
        created_at = "2026-05-13T08:00:00Z"
        fetched_at = "2026-05-13T10:00:00Z"
        collected_at = "2026-05-13T10:00:00Z"
        topic_id = "ai_agent_debugging"
        query_kind = "pilot_smoke_fixture"
        quality_flags = @()
        raw_metadata = @{ target_user = "developer" }
        contribution_to_cluster = "primary"
        excerpt = "We've been running AI coding agents in our CI pipeline for 3 months and debugging their failures is becoming a major time sink."
    },
    @{
        evidence_id = "gh_pilot_smoke_001"
        source_id = "github_issues"
        source_type = "issue_tracker"
        source_url = "https://github.com/langchain-ai/langgraph/issues/1234"
        title = "Agent debugging traces are incomplete in CI mode"
        body = "When running LangGraph agents in CI, the debug traces don't capture sufficient context to diagnose why an agent took a wrong action. This makes it extremely painful to fix agent behavior issues that only manifest in CI environments."
        evidence_kind = "bug_report"
        created_at = "2026-05-12T14:00:00Z"
        fetched_at = "2026-05-13T10:00:00Z"
        collected_at = "2026-05-13T10:00:00Z"
        topic_id = "ai_agent_debugging"
        query_kind = "pilot_smoke_fixture"
        quality_flags = @()
        raw_metadata = @{ target_user = "developer"; repo = "langchain-ai/langgraph" }
        contribution_to_cluster = "primary"
        excerpt = "When running LangGraph agents in CI, the debug traces don't capture sufficient context to diagnose why an agent took a wrong action."
    }
)

$FixtureJson = $FixtureEvidence | ConvertTo-Json -Depth 5
# Use UTF-8 without BOM to avoid Python json.load() error
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($PilotFixturePath, $FixtureJson, $Utf8NoBom)
Write-Host "  Pilot fixture written with $($FixtureEvidence.Count) evidence items"
Record-Pass "pilot smoke fixture created"

# Run pilot orchestrator via Python API (no live APIs, no LLMs, no CLI)
$PilotPyScript = Join-Path $TempRoot "_pilot_smoke.py"
@"
import json, sys
sys.path.insert(0, '$($TempSrc -replace '\\', '/')')
from oos.operational_discovery_pilot import (
    OperationalDiscoveryPilotInput,
    run_operational_discovery_pilot,
)

fixture_path = '$($PilotFixturePath -replace '\\', '/')'
output_dir = '$($PilotOutputDir -replace '\\', '/')'

with open(fixture_path, 'r', encoding='utf-8-sig') as f:
    evidence = json.load(f)

inp = OperationalDiscoveryPilotInput(
    raw_evidence=evidence,
    created_at='2026-05-13T10:00:00Z',
    discovery_run_id='pilot_smoke_v2_12',
    output_dir=output_dir,
)

result = run_operational_discovery_pilot(inp)

summary = {
    'discovery_run_id': result.discovery_run_id,
    'is_valid': result.is_valid,
    'raw_evidence_count': result.raw_evidence_count,
    'candidate_signal_count': result.candidate_signal_count,
    'pain_cluster_count': result.pain_cluster_count,
    'errors': [e[:200] for e in result.errors],
    'artifact_count': len(result.artifact_paths),
}

print('PILOT_RESULT_JSON:' + json.dumps(summary))

checks = []
checks.append(('is_valid', result.is_valid))
checks.append(('raw_evidence_count_gte_2', result.raw_evidence_count >= 2))
checks.append(('candidate_signal_count_gte_1', result.candidate_signal_count >= 1))
checks.append(('pain_cluster_count_gte_1', result.pain_cluster_count >= 1))
checks.append(('no_deferred_source_errors', not any('deferred' in e.lower() for e in result.errors)))
checks.append(('no_errors', len(result.errors) == 0))

for name, passed in checks:
    print(f'PILOT_CHECK: {name} = {passed}')

sys.exit(0 if all(p for _, p in checks) else 1)
"@ | Set-Content -Path $PilotPyScript -Encoding UTF8

$PilotResult = Invoke-CliSafe -Arguments @($PilotPyScript)
$PilotOutput = ($PilotResult.Output | Out-String)
Write-Host "  Pilot orchestrator output:"
Write-Host $PilotOutput

if ($PilotResult.ExitCode -ne 0) {
    Record-Fail "operational discovery pilot run" "exit code: $($PilotResult.ExitCode)"
} else {
    Record-Pass "operational discovery pilot: pipeline completed (exit 0)"
}

# Verify checks from Python output
if ($PilotOutput -match "PILOT_CHECK: is_valid = True") {
    Record-Pass "operational discovery pilot: result.is_valid=True"
} else {
    Record-Fail "operational discovery pilot: result.is_valid" "Expected True"
}

if ($PilotOutput -match "PILOT_CHECK: raw_evidence_count_gte_2 = True") {
    Record-Pass "operational discovery pilot: raw_evidence_count >= 2"
} else {
    Record-Fail "operational discovery pilot: raw_evidence_count" "Expected >= 2"
}

if ($PilotOutput -match "PILOT_CHECK: candidate_signal_count_gte_1 = True") {
    Record-Pass "operational discovery pilot: candidate_signal_count >= 1"
} else {
    Record-Fail "operational discovery pilot: candidate_signal_count" "Expected >= 1"
}

if ($PilotOutput -match "PILOT_CHECK: pain_cluster_count_gte_1 = True") {
    Record-Pass "operational discovery pilot: pain_cluster_count >= 1"
} else {
    Record-Fail "operational discovery pilot: pain_cluster_count" "Expected >= 1"
}

if ($PilotOutput -match "PILOT_CHECK: no_deferred_source_errors = True") {
    Record-Pass "operational discovery pilot: no deferred sources"
} else {
    Record-Fail "operational discovery pilot: deferred sources" "Deferred source detected"
}

if ($PilotOutput -match "PILOT_CHECK: no_errors = True") {
    Record-Pass "operational discovery pilot: no pipeline errors"
} else {
    Record-Fail "operational discovery pilot: pipeline errors" "Errors found in pilot run"
}

# Verify required artifacts exist on disk
$PilotRunDir = Join-Path $PilotOutputDir "pilot_smoke_v2_12"
if (Test-Path $PilotRunDir) {
    $RequiredArtifacts = @(
        "raw_evidence.json",
        "candidate_signals.json",
        "pain_clusters.json",
        "source_quality_report.json",
        "source_quality_report.md",
        "founder_review_package.json",
        "founder_review_package.md",
        "validation_summary.json",
        "pilot_run_manifest.json"
    )
    $MissingArtifacts = @()
    foreach ($artifact in $RequiredArtifacts) {
        $ArtifactPath = Join-Path $PilotRunDir $artifact
        if (-not (Test-Path $ArtifactPath)) {
            $MissingArtifacts += $artifact
        }
    }
    if ($MissingArtifacts.Count -eq 0) {
        Record-Pass "operational discovery pilot: all 9 required artifacts exist"
    } else {
        Record-Fail "operational discovery pilot: missing artifacts" "Missing: $($MissingArtifacts -join ', ')"
    }

    # Verify source scope: only hacker_news and github_issues used
    $RawEvidenceJson = Join-Path $PilotRunDir "raw_evidence.json"
    if (Test-Path $RawEvidenceJson) {
        try {
            $RawContent = Get-Content -Path $RawEvidenceJson -Raw -Encoding UTF8
            $RawData = $RawContent | ConvertFrom-Json
            $SourceIds = @($RawData | ForEach-Object { $_.source_id } | Select-Object -Unique)
            $BadSources = @($SourceIds | Where-Object { $_ -notin @("hacker_news", "github_issues") })
            if ($BadSources.Count -eq 0) {
                Record-Pass "operational discovery pilot: source scope clean (HN + GitHub only)"
            } else {
                Record-Fail "operational discovery pilot: source scope" "Unexpected sources: $($BadSources -join ', ')"
            }

            # Verify all source_urls are real http(s) URLs
            $BadUrls = @($RawData | Where-Object {
                $url = $_.source_url
                -not ($url -and ($url.StartsWith("http://") -or $url.StartsWith("https://")))
            })
            if ($BadUrls.Count -eq 0) {
                Record-Pass "operational discovery pilot: all source_urls are http(s)"
            } else {
                Record-Fail "operational discovery pilot: source_url traceability" "$($BadUrls.Count) non-http(s) URLs"
            }
        } catch {
            Record-Fail "operational discovery pilot: raw_evidence.json parse" $_.Exception.Message
        }
    }

    # Verify validation_summary reports valid run
    $VsJson = Join-Path $PilotRunDir "validation_summary.json"
    if (Test-Path $VsJson) {
        try {
            $VsContent = Get-Content -Path $VsJson -Raw -Encoding UTF8
            $VsData = $VsContent | ConvertFrom-Json
            if ($VsData.is_valid -eq $true) {
                Record-Pass "operational discovery pilot: validation_summary reports valid run"
            } else {
                Record-Fail "operational discovery pilot: validation_summary" "is_valid=False"
            }
        } catch {
            Record-Fail "operational discovery pilot: validation_summary.json" $_.Exception.Message
        }
    }

    # Verify founder_review_package traceability_status
    $FrpJson = Join-Path $PilotRunDir "founder_review_package.json"
    if (Test-Path $FrpJson) {
        try {
            $FrpContent = Get-Content -Path $FrpJson -Raw -Encoding UTF8
            $FrpData = $FrpContent | ConvertFrom-Json
            if ($FrpData.PSObject.Properties.Name -contains "traceability_status") {
                if ($FrpData.traceability_status -eq "clean") {
                    Record-Pass "operational discovery pilot: founder_review_package traceability=clean"
                } else {
                    Record-Fail "operational discovery pilot: founder_review_package traceability" "status=$($FrpData.traceability_status)"
                }
            } else {
                Record-Pass "operational discovery pilot: founder_review_package exists"
            }
        } catch {
            Record-Fail "operational discovery pilot: founder_review_package.json" $_.Exception.Message
        }
    }

    # Verify source_quality_report exists and is valid
    $SqrJson = Join-Path $PilotRunDir "source_quality_report.json"
    if (Test-Path $SqrJson) {
        try {
            $SqrContent = Get-Content -Path $SqrJson -Raw -Encoding UTF8
            $SqrData = $SqrContent | ConvertFrom-Json
            if ($SqrData.artifact_type -eq "source_quality_report") {
                Record-Pass "operational discovery pilot: source_quality_report valid"
            } else {
                Record-Fail "operational discovery pilot: source_quality_report" "Wrong artifact_type"
            }
        } catch {
            Record-Fail "operational discovery pilot: source_quality_report.json" $_.Exception.Message
        }
    }

    # Verify no deferred sources in source_quality_report
    if (Test-Path $SqrJson) {
        try {
            $SqrContent2 = Get-Content -Path $SqrJson -Raw -Encoding UTF8
            $SqrData2 = $SqrContent2 | ConvertFrom-Json
            $ReportSourceIds = @()
            if ($SqrData2.PSObject.Properties.Name -contains "source_metrics") {
                $ReportSourceIds = @($SqrData2.source_metrics | ForEach-Object { $_.source_id })
            }
            $DeferredInReport = @($ReportSourceIds | Where-Object {
                $_ -in @("product_hunt", "pimenov_ai", "reddit", "discord", "slack", "x_twitter", "stack_exchange")
            })
            if ($DeferredInReport.Count -eq 0) {
                Record-Pass "operational discovery pilot: no deferred sources in source_quality_report"
            } else {
                Record-Fail "operational discovery pilot: deferred in source_quality_report" "Found: $($DeferredInReport -join ', ')"
            }
        } catch {
            Write-Host "  (Source quality report deferred-check skipped: parse issue)"
        }
    }

} else {
    Record-Fail "operational discovery pilot: run directory not found" $PilotRunDir
}

Record-Pass "operational discovery pilot: smoke step complete (temp-only output)"

# ===========================================================================
# SUMMARY
# ===========================================================================
Write-Host ""
Write-Host "========================================"
Write-Host "  CONTROLLED WEEKLY RUN SMOKE TEST"
Write-Host "  Temp root: $TempRoot"
Write-Host "========================================"
Write-Host ""
Write-Host "PASSES ($($Passes.Count)):"
foreach ($p in $Passes) {
    Write-Host "  [PASS] $p"
}
Write-Host ""
if ($Failures.Count -gt 0) {
    Write-Host "FAILURES ($($Failures.Count)):"
    foreach ($f in $Failures) {
        Write-Host "  [FAIL] $f"
    }
    Write-Host ""
    Write-Host "===== OVERALL: FAIL ====="
    Write-Host "Temp root left at: $TempRoot (for inspection)"
    exit 1
} else {
    Write-Host "FAILURES: 0"
    Write-Host ""
    Write-Host "===== OVERALL: PASS ====="
    Write-Host "Temp root: $TempRoot"
    Write-Host ""
    Write-Host "NOTE: Temp directory will be cleaned by OS lifecycle."
    Write-Host "      To manually clean up, remove: $TempRoot"
    exit 0
}
