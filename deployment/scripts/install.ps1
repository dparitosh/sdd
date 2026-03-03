###############################################################################
# MBSE Knowledge Graph - Installation Script (DEPRECATED LOCATION)
# This script has been moved to scripts/install.ps1
# This wrapper forwards to the new location for backward compatibility.
###############################################################################

Write-Host "[NOTE] This script location is deprecated." -ForegroundColor Yellow
Write-Host "       Please use: .\scripts\install.ps1" -ForegroundColor Yellow
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..\..\").FullName
$NewScript = Join-Path $ProjectRoot "scripts\install.ps1"

if (Test-Path $NewScript) {
    & $NewScript @args
    exit $LASTEXITCODE
} else {
    Write-Host "[ERROR] Could not find $NewScript" -ForegroundColor Red
    exit 1
}
