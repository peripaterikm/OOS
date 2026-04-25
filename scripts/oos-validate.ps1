$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$env:PYTHONPATH = "src"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Write-Host "OOS validation"
Write-Host "Project root: $ProjectRoot"
Write-Host "Python: $Python"
Write-Host "PYTHONPATH: $env:PYTHONPATH"
Write-Host ""

Write-Host "Running full unittest discovery"
& $Python -m unittest discover -s tests -p "test_*.py" -v
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Running scripts\verify.ps1"
& (Join-Path $ProjectRoot "scripts\verify.ps1")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "OOS validation complete."

