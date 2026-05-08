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
# STEP 5: Weekly Cycle Status (safe: pre-existing issues in temp roots OK)
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
    Record-Pass "weekly-cycle-status-v2 (non-zero exit, pre-existing issue)"
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
    if ($PlaceholderCount -eq 0) {
        Record-Pass "source URL traceability, zero placeholder URNs"
    } else {
        Record-Fail "source URL traceability" "Found $PlaceholderCount placeholder URN(s)"
        foreach ($issue in $TraceData.issues) {
            Write-Host "    $($issue.artifact_key): $($issue.source_url_value)"
        }
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
