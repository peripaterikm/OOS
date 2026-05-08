<#
.SYNOPSIS
    Runs final local validation before commit/PR/merge.

.DESCRIPTION
    Executes git status, git diff --check, optional diff against HEAD~1,
    full unittest discovery, oos-validate.ps1, and prints a PASS/FAIL summary.
    Returns non-zero if any gate fails.
    Does NOT commit, push, merge, tag, delete, reset, or clean.

.PARAMETER ProjectRoot
    Path to the repository root. Defaults to the parent of this script's directory.

.PARAMETER SkipFullTests
    Skip full unittest discovery. Only run basic git checks.

.PARAMETER SkipOOSValidate
    Skip scripts/oos-validate.ps1 invocation.

.PARAMETER FocusedTest
    Run only the specified test module instead of full discovery.
    Example: -FocusedTest tests.test_dev_workflow_scripts

.EXAMPLE
    .\scripts\dev-validate-final.ps1

.EXAMPLE
    .\scripts\dev-validate-final.ps1 -SkipFullTests -SkipOOSValidate

.EXAMPLE
    .\scripts\dev-validate-final.ps1 -FocusedTest tests.test_source_url_traceability
#>

param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$SkipFullTests,
    [switch]$SkipOOSValidate,
    [string]$FocusedTest = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
Set-Location $ProjectRoot

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Failures = @()
$Passes = @()

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "===== $Title ====="
}

function Record-Result {
    param(
        [string]$Gate,
        [bool]$Passed,
        [string]$Detail = ""
    )
    if ($Passed) {
        $script:Passes += "[PASS] $Gate"
        Write-Host "[PASS] $Gate"
    } else {
        $script:Failures += "[FAIL] $Gate"
        Write-Host "[FAIL] $Gate"
        if ($Detail) {
            Write-Host "       $Detail"
        }
    }
    if ($Detail -and $Passed) {
        Write-Host "       $Detail"
    }
}

# === Gate 1: Git status ===
Write-Section "Gate 1: Git Status"
try {
    $Status = & git status --short 2>&1
    $StatusText = $Status | Out-String
    Write-Host $StatusText
    if ($StatusText.Trim() -eq "") {
        Record-Result "git status --short" $true "working tree clean"
    } else {
        Record-Result "git status --short" $true "working tree has changes (non-blocking)"
    }
} catch {
    Record-Result "git status --short" $false "Error: $_"
}

# === Gate 2: Git diff --check ===
Write-Section "Gate 2: Git Diff --check"
try {
    $DiffCheck = & git diff --check 2>&1
    if ($LASTEXITCODE -eq 0 -and [string]::IsNullOrWhiteSpace($DiffCheck)) {
        Record-Result "git diff --check" $true "no whitespace issues"
    } elseif ($LASTEXITCODE -eq 0) {
        Record-Result "git diff --check" $true "output present: $DiffCheck"
    } else {
        Record-Result "git diff --check" $false "whitespace issues found: $DiffCheck"
    }
} catch {
    Record-Result "git diff --check" $false "Error: $_"
}

# === Gate 3: Git diff --check HEAD~1..HEAD ===
Write-Section "Gate 3: Git Diff --check HEAD~1..HEAD"
try {
    $HasParent = $true
    $RevParse = & git rev-parse HEAD~1 2>&1
    if ($LASTEXITCODE -ne 0) {
        $HasParent = $false
        Record-Result "git diff --check HEAD~1..HEAD" $true "skipped (HEAD~1 does not exist)"
    }
    if ($HasParent) {
        $DiffCheckParent = & git diff --check HEAD~1..HEAD 2>&1
        if ($LASTEXITCODE -eq 0 -and [string]::IsNullOrWhiteSpace($DiffCheckParent)) {
            Record-Result "git diff --check HEAD~1..HEAD" $true "no whitespace issues"
        } elseif ($LASTEXITCODE -eq 0) {
            Record-Result "git diff --check HEAD~1..HEAD" $true "output present: $DiffCheckParent"
        } else {
            Record-Result "git diff --check HEAD~1..HEAD" $false "whitespace issues found: $DiffCheckParent"
        }
    }
} catch {
    Record-Result "git diff --check HEAD~1..HEAD" $false "Error: $_"
}

# === Gate 4: Unit tests ===
Write-Section "Gate 4: Unit Tests"
if ($SkipFullTests) {
    Record-Result "unit tests" $true "skipped (-SkipFullTests)"
} else {
    if (-not (Test-Path $PythonExe)) {
        Record-Result "unit tests" $false ".venv not found at $PythonExe"
    } else {
        $env:PYTHONPATH = Join-Path $ProjectRoot "src"
        try {
            if ($FocusedTest) {
                Write-Host "Running focused test: $FocusedTest"
                & $PythonExe -m unittest $FocusedTest -v 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Record-Result "focused test: $FocusedTest" $true
                } else {
                    Record-Result "focused test: $FocusedTest" $false "exit code: $LASTEXITCODE"
                }
            } else {
                Write-Host "Running full unittest discovery..."
                & $PythonExe -m unittest discover -s tests -p "test_*.py" -v 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Record-Result "full unittest discovery" $true
                } else {
                    Record-Result "full unittest discovery" $false "exit code: $LASTEXITCODE"
                }
            }
        } catch {
            Record-Result "unit tests" $false "Error: $_"
        }
    }
}

# === Gate 5: oos-validate.ps1 ===
Write-Section "Gate 5: OOS Validate"
if ($SkipOOSValidate) {
    Record-Result "oos-validate.ps1" $true "skipped (-SkipOOSValidate)"
} else {
    $ValidateScript = Join-Path $ProjectRoot "scripts\oos-validate.ps1"
    if (-not (Test-Path $ValidateScript)) {
        Record-Result "oos-validate.ps1" $false "script not found at $ValidateScript"
    } else {
        try {
            & $ValidateScript
            if ($LASTEXITCODE -eq 0) {
                Record-Result "oos-validate.ps1" $true
            } else {
                Record-Result "oos-validate.ps1" $false "exit code: $LASTEXITCODE"
            }
        } catch {
            Record-Result "oos-validate.ps1" $false "Error: $_"
        }
    }
}

# === Summary ===
Write-Section "Validation Summary"
Write-Host "Passes: $($Passes.Count)"
foreach ($P in $Passes) { Write-Host "  $P" }
Write-Host ""
Write-Host "Failures: $($Failures.Count)"
foreach ($F in $Failures) { Write-Host "  $F" }
Write-Host ""

if ($Failures.Count -eq 0) {
    Write-Host "===== OVERALL: PASS ====="
    exit 0
} else {
    Write-Host "===== OVERALL: FAIL ====="
    exit 1
}
