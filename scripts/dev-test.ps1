<#
.SYNOPSIS
    Runs Python unittests via the project's .venv with PYTHONPATH set to src.

.DESCRIPTION
    A safe, Windows-native unittest wrapper that:
    - Sets PYTHONPATH=src internally
    - Uses .\.venv\Scripts\python.exe
    - Supports targeted -Suite runs and -Full discovery
    - Prints a clear PASS/FAIL summary
    - Returns exit code 0 on all tests pass, exit code 1 on any test failure

    Does NOT chain shell commands via pipes/findstr/cmd.exe constructs,
    run git operations (add/commit/push/merge/tag/reset/clean),
    run gh pr create / gh pr merge, delete files, call live APIs/LLMs,
    or use Unix/bash/WSL constructs.

.PARAMETER ProjectRoot
    Path to the repository root. Defaults to the parent of this script's
    directory.

.PARAMETER Suite
    One or more dotted test module names to run.
    Multiple suites can be comma-separated or passed as repeated -Suite
    arguments.
    Example: -Suite tests.test_founder_decision_import_v2
    Example: -Suite tests.test_foo,tests.test_bar

.PARAMETER Full
    Run full unittest discovery across all tests/
    (python -m unittest discover -s tests -p test_*.py).

.PARAMETER Verbose
    Pass -v to unittest for verbose output.

.PARAMETER Summary
    Print only the final PASS/FAIL summary, suppressing per-test detail.

.EXAMPLE
    .\scripts\dev-test.ps1 -Suite tests.test_founder_decision_import_v2 -Verbose

.EXAMPLE
    .\scripts\dev-test.ps1 -Suite tests.test_dev_workflow_scripts,tests.test_dev_git_check_null_guard -Verbose

.EXAMPLE
    .\scripts\dev-test.ps1 -Full -Verbose

.EXAMPLE
    .\scripts\dev-test.ps1 -Full -Verbose -Summary
#>

param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string[]]$Suite,
    [switch]$Full,
    [switch]$Verbose,
    [switch]$Summary
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
Set-Location $ProjectRoot

# --- Validate -Suite / -Full ---

$HasSuite = ($null -ne $Suite) -and ($Suite.Count -gt 0)
$HasFull = $Full.IsPresent

if (-not $HasSuite -and -not $HasFull) {
    Write-Host "ERROR: You must pass -Suite or -Full."
    Write-Host "Usage:"
    Write-Host "  .\scripts\dev-test.ps1 -Suite <module> [-Verbose] [-Summary]"
    Write-Host "  .\scripts\dev-test.ps1 -Full [-Verbose] [-Summary]"
    exit 1
}

if ($HasSuite -and $HasFull) {
    Write-Host "ERROR: You cannot pass both -Suite and -Full."
    exit 1
}

# --- Resolve Python ---

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: Python venv not found at $PythonExe"
    Write-Host "Run scripts/bootstrap.ps1 first."
    exit 1
}

$env:PYTHONPATH = Join-Path $ProjectRoot "src"

$AllPassed = $true
$ExitCode = 0

# --- Run ---

if ($HasFull) {
    Write-Host "Running full unittest discovery..."
    Write-Host "PYTHONPATH=$env:PYTHONPATH"
    Write-Host "Python: $PythonExe"
    Write-Host ""

    $Args = @("-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py")
    if ($Verbose.IsPresent) { $Args += "-v" }

    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        if ($Summary.IsPresent) {
            $Output = & $PythonExe @Args 2>&1
            $TestExitCode = $LASTEXITCODE
        } else {
            & $PythonExe @Args 2>&1
            $TestExitCode = $LASTEXITCODE
        }
        if ($TestExitCode -ne 0) {
            if ($Summary.IsPresent) {
                Write-Host ($Output | Out-String)
            }
            $AllPassed = $false
            $ExitCode = $TestExitCode
        }
    } catch {
        Write-Host "ERROR: $_"
        $AllPassed = $false
        $ExitCode = 1
    } finally {
        $ErrorActionPreference = $prevEAP
    }
} else {
    Write-Host "Running suites: $($Suite -join ', ')"
    Write-Host "PYTHONPATH=$env:PYTHONPATH"
    Write-Host "Python: $PythonExe"
    Write-Host ""

    foreach ($Module in $Suite) {
        $ModuleName = $Module.Trim()
        Write-Host "--- $ModuleName ---"

        $Args = @("-m", "unittest", $ModuleName)
        if ($Verbose.IsPresent) { $Args += "-v" }

        $prevEAP = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            if ($Summary.IsPresent) {
                $Output = & $PythonExe @Args 2>&1
                $TestExitCode = $LASTEXITCODE
            } else {
                & $PythonExe @Args 2>&1
                $TestExitCode = $LASTEXITCODE
            }
            if ($TestExitCode -ne 0) {
                if ($Summary.IsPresent) {
                    Write-Host ($Output | Out-String)
                }
                $AllPassed = $false
                if ($ExitCode -eq 0) { $ExitCode = $TestExitCode }
            }
        } catch {
            Write-Host "ERROR in $ModuleName : $_"
            $AllPassed = $false
            if ($ExitCode -eq 0) { $ExitCode = 1 }
        } finally {
            $ErrorActionPreference = $prevEAP
        }
    }
}

# --- Summary ---

Write-Host ""
Write-Host "===== OVERALL: $(
    if ($AllPassed) { "PASS" } else { "FAIL" }
) ====="

exit $(if ($AllPassed) { 0 } else { 1 })
