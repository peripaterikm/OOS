param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$VenvDir = Join-Path $ProjectRoot ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$RequirementsPath = Join-Path $ProjectRoot "requirements.txt"

function Invoke-Checked {
    param([scriptblock]$ScriptBlock)

    & $ScriptBlock
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE."
    }
}

Write-Host "OOS Windows bootstrap"
Write-Host "Project root: $ProjectRoot"

if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating native Windows virtual environment at .venv"
    if (Get-Command py -ErrorAction SilentlyContinue) {
        Invoke-Checked { py -3 -m venv $VenvDir }
    }
    else {
        Invoke-Checked { python -m venv $VenvDir }
    }
}
else {
    Write-Host "Using existing native Windows virtual environment at .venv"
}

Write-Host "Upgrading pip"
Invoke-Checked { & $PythonExe -m pip install --upgrade pip }

if (Test-Path $RequirementsPath) {
    Write-Host "Installing requirements.txt"
    Invoke-Checked { & $PythonExe -m pip install -r $RequirementsPath }
}

Write-Host "Installing OOS in editable mode"
Invoke-Checked { & $PythonExe -m pip install -e $ProjectRoot }

Write-Host ""
Write-Host "Bootstrap complete."
Write-Host "Activate with:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
