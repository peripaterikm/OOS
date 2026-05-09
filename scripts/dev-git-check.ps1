<#
.SYNOPSIS
    Runs read-only Git control checks after a local commit.

.DESCRIPTION
    Prints current branch, git status --short, git log -8 --oneline,
    git show --stat --oneline HEAD, git diff --check, and
    git diff --check HEAD~1..HEAD. Returns exit code 0 if the working tree
    is clean and all whitespace checks pass. Returns exit code 1 if the
    working tree is dirty, whitespace issues exist, or any command fails
    unexpectedly.

    Does NOT stage, commit, push, merge, tag, reset, clean, delete files,
    or call live APIs/LLMs.

.PARAMETER ProjectRoot
    Path to the repository root. Defaults to the parent of this script's
    directory.

.EXAMPLE
    .\scripts\dev-git-check.ps1

.EXAMPLE
    .\scripts\dev-git-check.ps1 -ProjectRoot C:\MyProjects\OOS
#>

param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
Set-Location $ProjectRoot

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
    }
    if ($Detail) {
        Write-Host "       $Detail"
    }
}

# === Section 1: Current branch ===
Write-Section "Current Branch"
try {
    $Branch = & git branch --show-current 2>&1
    Write-Host $Branch
    Record-Result "git branch --show-current" $true
} catch {
    Record-Result "git branch --show-current" $false "Error: $_"
}

# === Section 2: Git status ===
Write-Section "Git Status (--short)"
try {
    $Status = & git status --short 2>&1
    $StatusText = ($Status | Out-String).Trim()
    if ($StatusText) {
        Write-Host $StatusText
        Record-Result "git status --short" $false "working tree is dirty"
    } else {
        Write-Host "(clean)"
        Record-Result "git status --short" $true "working tree clean"
    }
} catch {
    Record-Result "git status --short" $false "Error: $_"
}

# === Section 3: Git log ===
Write-Section "Git Log (last 8)"
try {
    $Log = & git log -8 --oneline 2>&1
    Write-Host ($Log | Out-String)
    Record-Result "git log -8 --oneline" $true
} catch {
    Record-Result "git log -8 --oneline" $false "Error: $_"
}

# === Section 4: HEAD summary ===
Write-Section "HEAD Summary"
try {
    $HeadShow = & git show --stat --oneline HEAD 2>&1
    Write-Host ($HeadShow | Out-String)
    Record-Result "git show --stat --oneline HEAD" $true
} catch {
    Record-Result "git show --stat --oneline HEAD" $false "Error: $_"
}

# === Section 5: Git diff --check (working tree) ===
Write-Section "Git Diff --check (working tree)"
try {
    $DiffCheck = & git diff --check 2>&1
    if ($LASTEXITCODE -eq 0 -and [string]::IsNullOrWhiteSpace($DiffCheck)) {
        Record-Result "git diff --check" $true "no whitespace issues"
    } elseif ($LASTEXITCODE -eq 0) {
        Write-Host $DiffCheck
        Record-Result "git diff --check" $true "output present (whitespace notes)"
    } else {
        Write-Host $DiffCheck
        Record-Result "git diff --check" $false "whitespace issues found"
    }
} catch {
    Record-Result "git diff --check" $false "Error: $_"
}

# === Section 6: Git diff --check HEAD~1..HEAD ===
Write-Section "Git Diff --check HEAD~1..HEAD"
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
            Write-Host $DiffCheckParent
            Record-Result "git diff --check HEAD~1..HEAD" $true "output present (whitespace notes)"
        } else {
            Write-Host $DiffCheckParent
            Record-Result "git diff --check HEAD~1..HEAD" $false "whitespace issues found"
        }
    }
} catch {
    Record-Result "git diff --check HEAD~1..HEAD" $false "Error: $_"
}

# === Summary ===
Write-Section "Git Check Summary"
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
