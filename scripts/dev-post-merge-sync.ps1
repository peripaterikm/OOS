<#
.SYNOPSIS
    Print and optionally perform safe local sync after PR merge.

.DESCRIPTION
    Default behavior is dry-run / instructions-only: shows current branch
    and suggested manual commands.
    With -ExecuteSafeSync, performs only safe operations:
    git switch main, git pull --ff-only, git fetch --prune, git status.
    Does NOT delete local/remote branches, push, merge, or tag.

.PARAMETER ProjectRoot
    Path to the repository root. Defaults to the parent of this script's directory.

.PARAMETER ExecuteSafeSync
    Execute the safe sync commands instead of dry-run.

.EXAMPLE
    .\scripts\dev-post-merge-sync.ps1

.EXAMPLE
    .\scripts\dev-post-merge-sync.ps1 -ExecuteSafeSync
#>

param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$ExecuteSafeSync
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
Set-Location $ProjectRoot

Write-Host "OOS Post-Merge Sync"
Write-Host "Project root: $ProjectRoot"
Write-Host ""

# === Show current state ===
Write-Host "===== Current Branch ====="
try {
    $Branch = & git branch --show-current 2>&1
    Write-Host "Current branch: $Branch"
} catch {
    Write-Host "ERROR: Could not determine current branch: $_"
    exit 1
}
Write-Host ""

# === Show recent commits ===
Write-Host "===== Recent Commits (last 5) ====="
try {
    & git log -5 --oneline --decorate 2>&1
} catch {
    Write-Host "(could not retrieve log)"
}
Write-Host ""

if (-not $ExecuteSafeSync) {
    # ===== DRY-RUN MODE =====
    Write-Host "===== DRY-RUN MODE (-ExecuteSafeSync not passed) ====="
    Write-Host ""
    Write-Host "Suggested manual commands after PR merge:"
    Write-Host ""
    Write-Host "  git switch main"
    Write-Host "  git pull --ff-only"
    Write-Host "  git fetch --prune"
    Write-Host "  git status --short"
    Write-Host ""
    Write-Host "To execute these commands automatically, re-run with -ExecuteSafeSync:"
    Write-Host "  .\scripts\dev-post-merge-sync.ps1 -ExecuteSafeSync"
    Write-Host ""
    Write-Host "NOTE: This script will NOT:"
    Write-Host "  - Delete local branches"
    Write-Host "  - Delete remote branches"
    Write-Host "  - Push"
    Write-Host "  - Merge"
    Write-Host "  - Tag"
    Write-Host ""
    Write-Host "No branches were deleted by this script."
    Write-Host "Manual cleanup of merged feature branches is left to the developer."
    exit 0
}

# ===== EXECUTION MODE =====
Write-Host "===== EXECUTION MODE (-ExecuteSafeSync) ====="
Write-Host "Performing safe sync operations only."
Write-Host ""

$Errors = @()

# 1. git switch main
Write-Host "--- Step 1: git switch main ---"
try {
    & git switch main 2>&1
    if ($LASTEXITCODE -ne 0) {
        $Errors += "git switch main failed with exit code $LASTEXITCODE"
        Write-Host "WARNING: Could not switch to main. Continuing with remaining steps..."
    } else {
        Write-Host "Switched to main."
    }
} catch {
    $Errors += "git switch main error: $_"
}

# 2. git pull --ff-only
Write-Host ""
Write-Host "--- Step 2: git pull --ff-only ---"
try {
    & git pull --ff-only 2>&1
    if ($LASTEXITCODE -ne 0) {
        $Errors += "git pull --ff-only failed with exit code $LASTEXITCODE"
        Write-Host "WARNING: git pull --ff-only may have failed."
    } else {
        Write-Host "Pull complete."
    }
} catch {
    $Errors += "git pull --ff-only error: $_"
}

# 3. git fetch --prune
Write-Host ""
Write-Host "--- Step 3: git fetch --prune ---"
try {
    & git fetch --prune 2>&1
    if ($LASTEXITCODE -ne 0) {
        $Errors += "git fetch --prune failed with exit code $LASTEXITCODE"
    } else {
        Write-Host "Fetch prune complete."
    }
} catch {
    $Errors += "git fetch --prune error: $_"
}

# 4. git status
Write-Host ""
Write-Host "--- Step 4: git status --short ---"
try {
    $Status = & git status --short 2>&1
    if ($Status) {
        Write-Host $Status
    } else {
        Write-Host "(clean)"
    }
} catch {
    $Errors += "git status error: $_"
}

Write-Host ""
Write-Host "===== Sync Summary ====="
if ($Errors.Count -eq 0) {
    Write-Host "Sync complete. All operations succeeded."
    Write-Host ""
    Write-Host "REMINDER:"
    Write-Host "  - Merged feature branches should be manually deleted when ready."
    Write-Host "  - No branches were deleted by this script."
    Write-Host "  - No push, merge, or tag was performed."
    exit 0
} else {
    Write-Host "Sync completed with errors:"
    foreach ($Err in $Errors) { Write-Host "  [ERROR] $Err" }
    exit 1
}
