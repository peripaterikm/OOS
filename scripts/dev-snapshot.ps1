<#
.SYNOPSIS
    Creates a local diagnostic snapshot file under _local_hold/dev_snapshots/.

.DESCRIPTION
    Captures timestamp, current branch, git status, recent log, diff check,
    and HEAD summary. Writes only to _local_hold/dev_snapshots/.
    Does NOT stage, commit, push, merge, tag, delete, or modify repo files.

.PARAMETER ProjectRoot
    Path to the repository root. Defaults to the parent of this script's directory.

.EXAMPLE
    .\scripts\dev-snapshot.ps1

.EXAMPLE
    .\scripts\dev-snapshot.ps1 -ProjectRoot C:\MyProjects\OOS
#>

param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
Set-Location $ProjectRoot

# === Safe write target ===
$SnapshotDir = Join-Path $ProjectRoot "_local_hold\dev_snapshots"
if (-not (Test-Path $SnapshotDir)) {
    New-Item -ItemType Directory -Path $SnapshotDir -Force | Out-Null
}

$Timestamp = (Get-Date -Format "yyyy-MM-dd_HHmmss")
$SnapshotFile = Join-Path $SnapshotDir "dev_snapshot_${Timestamp}.txt"

# === Collect snapshot data ===
$Lines = @()

$Lines += "=== OOS Developer Snapshot ==="
$Lines += "Timestamp (local): $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
$Lines += "Timestamp (UTC)  : $((Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss'))"
$Lines += "Project root     : $ProjectRoot"
$Lines += "Snapshot file    : $SnapshotFile"
$Lines += ""

# Current branch
$Lines += "=== Current Branch ==="
try {
    $Branch = & git branch --show-current 2>&1
    $Lines += $Branch
} catch {
    $Lines += "ERROR: git branch --show-current failed: $_"
}
$Lines += ""

# Git status
$Lines += "=== Git Status (short) ==="
try {
    $Status = & git status --short 2>&1
    $Lines += $Status
} catch {
    $Lines += "ERROR: git status --short failed: $_"
}
$Lines += ""

# Git log
$Lines += "=== Git Log (last 10) ==="
try {
    $Log = & git log -10 --oneline --decorate 2>&1
    $Lines += $Log
} catch {
    $Lines += "ERROR: git log failed: $_"
}
$Lines += ""

# Git diff --check
$Lines += "=== Git Diff --check ==="
try {
    $DiffCheck = & git diff --check 2>&1
    if ($DiffCheck) {
        $Lines += $DiffCheck
    } else {
        $Lines += "(clean)"
    }
} catch {
    $Lines += "ERROR: git diff --check failed: $_"
}
$Lines += ""

# HEAD summary
$Lines += "=== HEAD Summary ==="
try {
    $HeadShow = & git show --stat --oneline HEAD 2>&1
    $Lines += $HeadShow
} catch {
    $Lines += "ERROR: git show HEAD failed: $_"
}
$Lines += ""

# Roadmap state excerpts (best-effort, non-fatal)
$Lines += "=== Roadmap State Excerpts ==="
$RoadmapFile = Join-Path $ProjectRoot "docs\roadmaps\OOS_roadmap_v2_7_traceability_and_real_run_readiness_checklist.md"
if (Test-Path $RoadmapFile) {
    try {
        $RoadmapLines = Get-Content $RoadmapFile -Encoding UTF8
        foreach ($Line in $RoadmapLines) {
            if ($Line -match "Current item|Completed from this roadmap|Remaining:|Roadmap state") {
                $Lines += $Line
            }
        }
    } catch {
        $Lines += "(could not read roadmap file)"
    }
} else {
    $Lines += "(roadmap file not found)"
}
$Lines += ""

$ProjectStateFile = Join-Path $ProjectRoot "docs\dev_ledger\00_project_state.md"
if (Test-Path $ProjectStateFile) {
    try {
        $StateLines = Get-Content $ProjectStateFile -Encoding UTF8
        $Found = $false
        foreach ($Line in $StateLines) {
            if ($Line -match "Current item:|Completed:|Remaining:|Latest completed|Next planned") {
                $Lines += $Line
                $Found = $true
            }
        }
        if (-not $Found) {
            $Lines += "(no state lines matched)"
        }
    } catch {
        $Lines += "(could not read project state file)"
    }
} else {
    $Lines += "(project state file not found)"
}
$Lines += ""

$Lines += "=== Snapshot Complete ==="

# === Write snapshot ===
$Lines -join "`r`n" | Out-File -FilePath $SnapshotFile -Encoding UTF8

Write-Host "Snapshot written to: $SnapshotFile"
Write-Host ""

# Print snapshot to console too
Write-Host ($Lines -join "`r`n")

exit 0
