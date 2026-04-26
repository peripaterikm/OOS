param(
    [Parameter(Mandatory = $true)]
    [string]$ReportPath,

    [string[]]$FocusedTest = @()
)

$ErrorActionPreference = "Continue"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$env:PYTHONPATH = "src"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ResolvedReportPath = Join-Path $ProjectRoot $ReportPath
$ReportDirectory = Split-Path -Parent $ResolvedReportPath
if (!(Test-Path $ReportDirectory)) {
    New-Item -ItemType Directory -Path $ReportDirectory | Out-Null
}

$LogPath = [System.IO.Path]::ChangeExtension($ResolvedReportPath, ".log")
$StartedAt = (Get-Date).ToString("o")
$OverallExitCode = 0

@"
# OOS Validation Report

- Started at: `$StartedAt`
- Working directory: `$ProjectRoot`
- PYTHONPATH: `$env:PYTHONPATH`
- Full log: `$LogPath`

## Commands Run

"@ | Set-Content -Path $ResolvedReportPath -Encoding UTF8

"" | Set-Content -Path $LogPath -Encoding UTF8

function Invoke-ValidationCommand {
    param(
        [string]$Name,
        [string]$CommandText,
        [scriptblock]$Command
    )

    Add-Content -Path $ResolvedReportPath -Encoding UTF8 -Value "### $Name"
    Add-Content -Path $ResolvedReportPath -Encoding UTF8 -Value ""
    Add-Content -Path $ResolvedReportPath -Encoding UTF8 -Value "- Command: ``$CommandText``"
    Add-Content -Path $LogPath -Encoding UTF8 -Value "### $Name"
    Add-Content -Path $LogPath -Encoding UTF8 -Value $CommandText

    & $Command *>&1 | Tee-Object -FilePath $LogPath -Append
    $ExitCode = $LASTEXITCODE
    if ($null -eq $ExitCode) {
        $ExitCode = 0
    }

    if ($ExitCode -eq 0) {
        Add-Content -Path $ResolvedReportPath -Encoding UTF8 -Value "- Result: pass"
    } else {
        Add-Content -Path $ResolvedReportPath -Encoding UTF8 -Value "- Result: fail ($ExitCode)"
        $script:OverallExitCode = $ExitCode
    }
    Add-Content -Path $ResolvedReportPath -Encoding UTF8 -Value ""
}

foreach ($Focused in $FocusedTest) {
    Invoke-ValidationCommand `
        -Name "Focused test: $Focused" `
        -CommandText "`$env:PYTHONPATH=`"src`"; .\.venv\Scripts\python.exe -m unittest $Focused -v" `
        -Command { & $Python -m unittest $Focused -v }
}

Invoke-ValidationCommand `
    -Name "Full unittest discovery" `
    -CommandText "`$env:PYTHONPATH=`"src`"; .\.venv\Scripts\python.exe -m unittest discover -s tests -p `"test_*.py`" -v" `
    -Command { & $Python -m unittest discover -s tests -p "test_*.py" -v }

Invoke-ValidationCommand `
    -Name "Project validation" `
    -CommandText ".\scripts\oos-validate.ps1" `
    -Command { & (Join-Path $ProjectRoot "scripts\oos-validate.ps1") }

Invoke-ValidationCommand `
    -Name "Final verification" `
    -CommandText ".\scripts\verify.ps1" `
    -Command { & (Join-Path $ProjectRoot "scripts\verify.ps1") }

Invoke-ValidationCommand `
    -Name "Diff whitespace check" `
    -CommandText "git diff --check" `
    -Command { git diff --check }

$CompletedAt = (Get-Date).ToString("o")

@"
## Results Summary

- Completed at: `$CompletedAt`
- Overall result: $(if ($OverallExitCode -eq 0) { "pass" } else { "fail ($OverallExitCode)" })

## Blocked Commands

- None recorded by helper.

## Known Warnings

- `.test-tmp` / `.tmp_tests` ACL warnings are known local artifacts and should not be staged.

## Safety Confirmation

- No push performed.
- No merge performed.
- No tag created.
- No release created.
- No live LLM/API calls made by this helper.
"@ | Add-Content -Path $ResolvedReportPath -Encoding UTF8

exit $OverallExitCode
