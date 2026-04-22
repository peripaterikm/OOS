param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$DryRunProjectRoot = "",
    [switch]$SkipDryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    throw "Missing .venv. Run .\scripts\bootstrap.ps1 first."
}

$env:PYTHONPATH = Join-Path $ProjectRoot "src"

function Invoke-Checked {
    param(
        [scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE."
    }
}

Write-Host "OOS Windows verification"
Write-Host "Project root: $ProjectRoot"
Write-Host "Python: $PythonExe"
Write-Host "PYTHONPATH: $env:PYTHONPATH"

Push-Location $ProjectRoot
try {
    Write-Host ""
    Write-Host "Running unit tests"
    Invoke-Checked { & $PythonExe -m unittest discover -s tests -p "test_*.py" -v }

    if (-not $SkipDryRun) {
        $RemoveDryRunRoot = $false
        if ([string]::IsNullOrWhiteSpace($DryRunProjectRoot)) {
            $DryRunProjectRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("oos-verify-" + [System.Guid]::NewGuid().ToString("N"))
            New-Item -ItemType Directory -Path $DryRunProjectRoot | Out-Null
            $RemoveDryRunRoot = $true
        }
        else {
            $DryRunProjectRoot = (Resolve-Path $DryRunProjectRoot).Path
        }

        Write-Host ""
        Write-Host "Running v1 dry run"
        Write-Host "Dry run project root: $DryRunProjectRoot"
        Invoke-Checked { & $PythonExe -m oos.cli v1-dry-run --project-root $DryRunProjectRoot }

        if ($RemoveDryRunRoot) {
            Remove-Item -LiteralPath $DryRunProjectRoot -Recurse -Force
        }
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Verification complete."
