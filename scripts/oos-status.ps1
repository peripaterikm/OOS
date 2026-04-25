$ErrorActionPreference = "Continue"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

Write-Host "OOS status"
Write-Host "Project root: $ProjectRoot"
Write-Host ""

Write-Host "Current branch:"
git branch --show-current
Write-Host ""

Write-Host "Last 5 commits:"
git log --oneline -n 5
Write-Host ""

Write-Host "Git status:"
git status --short
Write-Host ""

$Roadmap = Join-Path $ProjectRoot "docs\roadmaps\OOS_roadmap_v2_2_8_weeks_checklist.md"
if (Test-Path $Roadmap) {
    Write-Host "Active roadmap state:"
    Select-String -Path $Roadmap -Pattern "Current item|Completed from this roadmap|Remaining:" | ForEach-Object {
        Write-Host $_.Line
    }
    Write-Host ""
}

$ProjectState = Join-Path $ProjectRoot "docs\dev_ledger\00_project_state.md"
if (Test-Path $ProjectState) {
    Write-Host "Dev Ledger project state:"
    Select-String -Path $ProjectState -Pattern "Current item:|Completed:|Remaining:|Latest completed roadmap item:|Next planned roadmap item:" | ForEach-Object {
        Write-Host $_.Line
    }
}

