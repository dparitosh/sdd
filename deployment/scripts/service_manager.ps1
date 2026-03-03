###############################################################################
# MBSE Knowledge Graph - Service Manager (DEPRECATED LOCATION)
# This script has been moved to scripts/service_manager.ps1
# This wrapper forwards to the new location for backward compatibility.
###############################################################################

param(
    [Parameter(Position=0)]
    [string]$Command = 'help',
    
    [Parameter(Position=1)]
    [string]$SubCommand
)

Write-Host "[NOTE] This script location is deprecated." -ForegroundColor Yellow
Write-Host "       Please use: .\scripts\service_manager.ps1" -ForegroundColor Yellow
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..\..\").FullName
$NewScript = Join-Path $ProjectRoot "scripts\service_manager.ps1"

if (Test-Path $NewScript) {
    if ($SubCommand) {
        & $NewScript $Command $SubCommand
    } else {
        & $NewScript $Command
    }
    exit $LASTEXITCODE
} else {
    Write-Host "[ERROR] Could not find $NewScript" -ForegroundColor Red
    exit 1
}
