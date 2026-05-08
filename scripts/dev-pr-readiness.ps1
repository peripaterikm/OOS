<#
.SYNOPSIS
    Read-only PR readiness check.

.DESCRIPTION
    Prints branch info, HEAD commit, comparison to origin/main if available,
    git diff --check, roadmap/dev ledger update status, and a PR readiness
    reminder. Does NOT create PRs, push, merge, or call PR creation commands.

.PARAMETER ProjectRoot
    Path to the repository root. Defaults to the parent of this script's directory.

.EXAMPLE
    .\scripts\dev-pr-readiness.ps1

.EXAMPLE
    .\scripts\dev-pr-readiness.ps1 -ProjectRoot C:\MyProjects\OOS
#>

param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
Set-Location $ProjectRoot

$Blockers = @()
$Warnings = @()
$Info = @()

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "===== $Title ====="
}

function Add-Blocker {
    param([string]$Msg)
    $script:Blockers += $Msg
}

function Add-Warning {
    param([string]$Msg)
    $script:Warnings += $Msg
}

function Add-Info {
    param([string]$Msg)
    $script:Info += $Msg
}

# === 1. Current branch ===
Write-Section "1. Current Branch"
try {
    $Branch = & git branch --show-current 2>&1
    Write-Host "Branch: $Branch"
    Add-Info "Current branch: $Branch"
    $NormalizedBranch = $Branch.ToString().Trim()
    if ($NormalizedBranch -eq "main" -or $NormalizedBranch -eq "master") {
        Add-Blocker "Branch is '$NormalizedBranch'. PR should NOT be from main/master."
    }
} catch {
    Add-Blocker "Could not determine current branch: $_"
}

# === 2. HEAD commit ===
Write-Section "2. HEAD Commit"
try {
    $HeadCommit = & git log -1 --oneline --decorate 2>&1
    Write-Host $HeadCommit
    Add-Info "HEAD: $HeadCommit"
} catch {
    Add-Warning "Could not get HEAD commit: $_"
}

# === 3. Git status ===
Write-Section "3. Git Status"
try {
    $Status = & git status --short 2>&1
    if ($Status) {
        Write-Host $Status
        Add-Warning "Working tree has uncommitted changes."
    } else {
        Write-Host "(clean)"
        Add-Info "Working tree is clean."
    }
} catch {
    Add-Warning "Could not run git status: $_"
}

# === 4. Comparison to origin/main ===
Write-Section "4. Comparison to origin/main"
try {
    $FetchResult = & git fetch origin main 2>&1
    if ($LASTEXITCODE -ne 0) {
        Add-Warning "Could not fetch origin/main: $FetchResult"
    } else {
        $BehindAhead = & git rev-list --left-right --count origin/main...HEAD 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Commits behind origin/main: $($BehindAhead.Split()[0])"
            Write-Host "Commits ahead of origin/main: $($BehindAhead.Split()[1])"
            Add-Info "Behind: $($BehindAhead.Split()[0]), Ahead: $($BehindAhead.Split()[1])"
        }
        $DiffStat = & git diff --stat origin/main...HEAD 2>&1
        if ($LASTEXITCODE -eq 0 -and $DiffStat) {
            Write-Host ""
            Write-Host "Diff stat vs origin/main:"
            Write-Host $DiffStat
        }
    }
} catch {
    Add-Warning "Could not compare to origin/main: $_"
}

# === 5. Git diff --check ===
Write-Section "5. Git Diff --check"
try {
    $DiffCheck = & git diff --check 2>&1
    if ($LASTEXITCODE -eq 0 -and [string]::IsNullOrWhiteSpace($DiffCheck)) {
        Write-Host "(no whitespace issues)"
    } elseif ($LASTEXITCODE -eq 0) {
        Write-Host $DiffCheck
    } else {
        Add-Blocker "git diff --check found whitespace issues."
        Write-Host $DiffCheck
    }
} catch {
    Add-Warning "Could not run git diff --check: $_"
}

# === 6. Secure file check ===
Write-Section "6. Secure File Check (.env, .venv, artifacts, reports)"
try {
    $Staged = & git diff --cached --name-only 2>&1
    $TrackedNew = & git diff --cached --name-status 2>&1
    $AllTracked = & git ls-files 2>&1

    $SecurePatterns = @(".env", ".venv", "artifacts/", "reports/")
    $Violations = @()

    # Check staged files
    if ($Staged) {
        foreach ($File in $Staged) {
            foreach ($Pattern in $SecurePatterns) {
                if ($File -like "$Pattern*") {
                    $Violations += $File
                    break
                }
            }
        }
    }

    # Also check if .env or .venv are tracked at all
    if ($AllTracked) {
        foreach ($File in $AllTracked) {
            if ($File -eq ".env" -or $File -like ".env.*" -or $File -eq ".venv" -or $File -like ".venv/*") {
                if ($Violations -notcontains $File) {
                    $Violations += $File
                }
            }
        }
    }

    if ($Violations.Count -gt 0) {
        Add-Blocker "Secure files found in tracking/staging: $($Violations -join ', ')"
        Write-Host "[BLOCKED] $($Violations -join ', ')"
    } else {
        Write-Host "(no secure files in tracking/staging)"
        Add-Info "No .env, .venv, artifacts/, or reports/ files staged/tracked."
    }
} catch {
    Add-Warning "Could not complete secure file check: $_"
}

# === 7. Roadmap / Dev Ledger update check ===
Write-Section "7. Roadmap / Dev Ledger Update Check"
$RoadmapFile = Join-Path $ProjectRoot "docs\roadmaps\OOS_roadmap_v2_7_traceability_and_real_run_readiness_checklist.md"
$ProjectStateFile = Join-Path $ProjectRoot "docs\dev_ledger\00_project_state.md"

if (Test-Path $RoadmapFile) {
    try {
        $RoadmapContent = Get-Content $RoadmapFile -Encoding UTF8 -Raw
        if ($RoadmapContent -match "\[x\].*4\.1") {
            Write-Host "Roadmap: item 4.1 appears checked."
            Add-Info "Roadmap shows 4.1 complete."
        } elseif ($RoadmapContent -match "\[ \].*4\.1") {
            Write-Host "Roadmap: item 4.1 appears unchecked - may need update."
            Add-Warning "Roadmap item 4.1 still unchecked."
        } else {
            Write-Host "Roadmap: could not determine 4.1 status."
        }
    } catch {
        Add-Warning "Could not read roadmap file."
    }
} else {
    Add-Warning "Roadmap file not found."
}

if (Test-Path $ProjectStateFile) {
    try {
        $StateContent = Get-Content $ProjectStateFile -Encoding UTF8 -Raw
        if ($StateContent -match "Current item.*4\.1.*Developer workflow" -or $StateContent -match "Current item.*5\.1") {
            Write-Host "Dev Ledger: appears updated for item 4.1 or beyond."
            Add-Info "Dev Ledger shows current progress."
        } else {
            Write-Host "Dev Ledger: may need update."
            Add-Warning "Dev Ledger may need update for current item."
        }
    } catch {
        Add-Warning "Could not read dev ledger state file."
    }
} else {
    Add-Warning "Dev Ledger project state file not found."
}

# === 8. Mini-epic and run report check ===
Write-Section "8. Mini-Epic and Run Report Check"
$MiniEpicFile = Join-Path $ProjectRoot "docs\dev_ledger\02_mini_epics\4.1-developer-workflow-helper-scripts.md"
$RunReportFile = Join-Path $ProjectRoot "docs\dev_ledger\03_run_reports\4.1-developer-workflow-helper-scripts.md"

if (Test-Path $MiniEpicFile) {
    Write-Host "Mini-epic: exists"
    Add-Info "Mini-epic file present."
} else {
    Write-Host "Mini-epic: NOT FOUND"
    Add-Warning "Mini-epic file missing."
}

if (Test-Path $RunReportFile) {
    Write-Host "Run report: exists"
    Add-Info "Run report file present."
} else {
    Write-Host "Run report: NOT FOUND"
    Add-Warning "Run report file missing."
}

# === Summary ===
Write-Section "PR Readiness Summary"
Write-Host ""
if ($Blockers.Count -eq 0 -and $Warnings.Count -eq 0) {
    Write-Host "===== READY for PR ====="
} elseif ($Blockers.Count -eq 0) {
    Write-Host "===== READY for PR (with warnings) ====="
} else {
    Write-Host "===== NOT READY for PR ====="
}

if ($Blockers.Count -gt 0) {
    Write-Host ""
    Write-Host "BLOCKERS ($($Blockers.Count)):"
    foreach ($B in $Blockers) { Write-Host "  [BLOCKER] $B" }
}

if ($Warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "WARNINGS ($($Warnings.Count)):"
    foreach ($W in $Warnings) { Write-Host "  [WARNING] $W" }
}

Write-Host ""
Write-Host "REMINDER: PR creation must be manual. This script does NOT create PRs."
Write-Host "Use the GitHub CLI to open a pull request manually (do not automate)."
Write-Host ""

if ($Blockers.Count -gt 0) {
    exit 1
} else {
    exit 0
}
