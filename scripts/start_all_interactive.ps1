# Start backend + frontend with step-by-step console output
# Usage:
#   .\scripts\start_all_interactive.ps1
#   .\scripts\start_all_interactive.ps1 -Inspect

param(
    [switch]$Inspect
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location -LiteralPath $repoRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "MBSE Knowledge Graph - Interactive Startup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$mgr = Join-Path $repoRoot "scripts\service_manager.ps1"
if (!(Test-Path -LiteralPath $mgr)) {
    throw "Could not find service_manager.ps1 at: $mgr"
}

if ($Inspect) {
    & $mgr start -Interactive -Inspect
} else {
    & $mgr start -Interactive
}
