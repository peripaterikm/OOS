param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$VenvDir = Join-Path $ProjectRoot ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$RequirementsPath = Join-Path $ProjectRoot "requirements.txt"

Write-Host "OOS Windows bootstrap"
Write-Host "Project root: $ProjectRoot"

if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating native Windows virtual environment at .venv"
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3 -m venv $VenvDir
    }
    else {
        python -m venv $VenvDir
    }
}
else {
    Write-Host "Using existing native Windows virtual environment at .venv"
}

Write-Host "Upgrading pip"
& $PythonExe -m pip install --upgrade pip

if (Test-Path $RequirementsPath) {
    Write-Host "Installing requirements.txt"
    & $PythonExe -m pip install -r $RequirementsPath
}

Write-Host "Installing OOS in editable mode"
& $PythonExe -m pip install -e $ProjectRoot

Write-Host ""
Write-Host "Bootstrap complete."
Write-Host "Activate with:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
