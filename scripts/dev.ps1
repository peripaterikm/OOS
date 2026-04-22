param(
    [Parameter(Position = 0)]
    [ValidateSet("bootstrap", "verify", "dry-run", "founder-review-help", "help")]
    [string]$Command = "help",

    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$DryRunProjectRoot = "",
    [switch]$SkipDryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

function Invoke-Checked {
    param([scriptblock]$ScriptBlock)

    & $ScriptBlock
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE."
    }
}

function Require-Venv {
    if (-not (Test-Path $PythonExe)) {
        throw "Missing .venv. Run .\scripts\dev.ps1 bootstrap first."
    }
}

function New-TempDryRunRoot {
    $Path = Join-Path ([System.IO.Path]::GetTempPath()) ("oos-dev-dry-run-" + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $Path | Out-Null
    return $Path
}

function Write-DevHelp {
    Write-Host "OOS Windows developer entrypoint"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\scripts\dev.ps1 bootstrap"
    Write-Host "  .\scripts\dev.ps1 verify"
    Write-Host "  .\scripts\dev.ps1 dry-run"
    Write-Host "  .\scripts\dev.ps1 dry-run -DryRunProjectRoot ."
    Write-Host "  .\scripts\dev.ps1 founder-review-help"
    Write-Host ""
    Write-Host "Notes:"
    Write-Host "  dry-run uses a clean temporary project root by default."
    Write-Host "  pass -DryRunProjectRoot . to write dry-run artifacts under this repository."
}

if ($Command -eq "help") {
    Write-DevHelp
    exit 0
}

if ($Command -eq "bootstrap") {
    & (Join-Path $PSScriptRoot "bootstrap.ps1") -ProjectRoot $ProjectRoot
    exit 0
}

if ($Command -eq "verify") {
    if ([string]::IsNullOrWhiteSpace($DryRunProjectRoot)) {
        & (Join-Path $PSScriptRoot "verify.ps1") -ProjectRoot $ProjectRoot -SkipDryRun:$SkipDryRun
    }
    else {
        & (Join-Path $PSScriptRoot "verify.ps1") -ProjectRoot $ProjectRoot -DryRunProjectRoot $DryRunProjectRoot -SkipDryRun:$SkipDryRun
    }
    exit 0
}

Require-Venv
$env:PYTHONPATH = Join-Path $ProjectRoot "src"

if ($Command -eq "dry-run") {
    $RemoveDryRunRoot = $false
    if ([string]::IsNullOrWhiteSpace($DryRunProjectRoot)) {
        $DryRunProjectRoot = New-TempDryRunRoot
        $RemoveDryRunRoot = $true
    }
    else {
        $DryRunProjectRoot = (Resolve-Path $DryRunProjectRoot).Path
    }

    try {
        Write-Host "Running OOS v1 dry run"
        Write-Host "Project root: $ProjectRoot"
        Write-Host "Dry run project root: $DryRunProjectRoot"
        Invoke-Checked { & $PythonExe -m oos.cli v1-dry-run --project-root $DryRunProjectRoot }
    }
    finally {
        if ($RemoveDryRunRoot -and (Test-Path $DryRunProjectRoot)) {
            Remove-Item -LiteralPath $DryRunProjectRoot -Recurse -Force
        }
    }
    exit 0
}

if ($Command -eq "founder-review-help") {
    Write-Host "Founder review workflow"
    Write-Host "1) Generate a dry-run package:"
    Write-Host "   .\scripts\dev.ps1 dry-run -DryRunProjectRoot ."
    Write-Host "2) Open:"
    Write-Host "   artifacts\ops\v1_founder_review_checklist.md"
    Write-Host "3) Run one of the generated PowerShell-compatible record-founder-review commands."
    Write-Host ""
    Invoke-Checked { & $PythonExe -m oos.cli record-founder-review --help }
    exit 0
}
