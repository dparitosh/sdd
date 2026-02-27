###############################################################################
# MBSE Knowledge Graph - Cleanup Script (DEPRECATED LOCATION)
# This script has been moved to scripts/cleanup.ps1
# This wrapper forwards to the new location for backward compatibility.
###############################################################################

param(
    [switch]$IncludeNodeModules
)

Write-Host "[NOTE] This script location is deprecated." -ForegroundColor Yellow
Write-Host "       Please use: .\scripts\cleanup.ps1" -ForegroundColor Yellow
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..\..\").FullName
$NewScript = Join-Path $ProjectRoot "scripts\cleanup.ps1"

if (Test-Path $NewScript) {
    if ($IncludeNodeModules) {
        & $NewScript -IncludeNodeModules
    } else {
        & $NewScript
    }
    exit $LASTEXITCODE
} else {
    Write-Host "[ERROR] Could not find $NewScript" -ForegroundColor Red
    exit 1
}

Write-Host "=== Removing Python cache files ===" -ForegroundColor Cyan
Get-ChildItem -Path . -Directory -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Path . -File -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem -Path . -File -Recurse -Filter "*.pyo" -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem -Path . -File -Recurse -Filter "*.pyd" -ErrorAction SilentlyContinue | Remove-Item -Force
Write-Host "[SUCCESS] Python cache cleaned" -ForegroundColor Green
Write-Host ""

Write-Host "=== Removing test and coverage artifacts ===" -ForegroundColor Cyan
Remove-SafelyLocal -Path ".\.pytest_cache" -Description "pytest cache"
Remove-SafelyLocal -Path ".\.coverage" -Description "coverage data"
Remove-SafelyLocal -Path ".\htmlcov" -Description "HTML coverage report"
Remove-SafelyLocal -Path ".\.tox" -Description "tox environments"
Write-Host ""

Write-Host "=== Removing build artifacts ===" -ForegroundColor Cyan
Remove-SafelyLocal -Path ".\build" -Description "build directory"
Remove-SafelyLocal -Path ".\dist" -Description "distribution directory"
Get-ChildItem -Path . -Directory -Filter "*.egg-info" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Remove-SafelyLocal -Path ".\.eggs" -Description "eggs directory"
Write-Host ""

Write-Host "=== Removing Node.js artifacts ===" -ForegroundColor Cyan
Remove-SafelyLocal -Path ".\node_modules\.cache" -Description "Vite cache"
Remove-SafelyLocal -Path ".\.vite" -Description "Vite temp files"
Remove-SafelyLocal -Path ".\frontend\.vite" -Description "Frontend Vite temp files"
Write-Host ""

Write-Host "=== Removing log files ===" -ForegroundColor Cyan
Get-ChildItem -Path ".\logs" -Filter "*.log" -ErrorAction SilentlyContinue | Remove-Item -Force
Remove-Item -Path "$env:TEMP\backend.log" -ErrorAction SilentlyContinue
Remove-Item -Path "$env:TEMP\frontend.log" -ErrorAction SilentlyContinue
Remove-Item -Path "$env:TEMP\build.log" -ErrorAction SilentlyContinue
Write-Host "[SUCCESS] Log files removed" -ForegroundColor Green
Write-Host ""

Write-Host "=== Removing old backup files ===" -ForegroundColor Cyan
Get-ChildItem -Path . -File -Recurse -Filter "*.old" -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem -Path . -File -Recurse -Filter "*.bak" -ErrorAction SilentlyContinue | Remove-Item -Force
Write-Host "[SUCCESS] Backup files removed" -ForegroundColor Green
Write-Host ""

Write-Host "=== Removing OS-specific files ===" -ForegroundColor Cyan
Get-ChildItem -Path . -File -Recurse -Filter "Thumbs.db" -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem -Path . -File -Recurse -Filter "desktop.ini" -ErrorAction SilentlyContinue | Remove-Item -Force
Write-Host "[SUCCESS] Windows files removed" -ForegroundColor Green
Write-Host ""

Write-Host "=== Removing editor temporary files ===" -ForegroundColor Cyan
Get-ChildItem -Path . -File -Recurse -Filter "*.swp" -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem -Path . -File -Recurse -Filter "*.swo" -ErrorAction SilentlyContinue | Remove-Item -Force
Write-Host "[SUCCESS] Editor temp files removed" -ForegroundColor Green
Write-Host ""

Write-Host "=== Optional: Remove node_modules ===" -ForegroundColor Cyan
$response = Read-Host "Do you want to remove node_modules? (y/N)"
if ($response -eq 'y' -or $response -eq 'Y') {
    if (Test-Path ".\node_modules") {
        Write-Host "Removing node_modules..." -ForegroundColor Yellow
        Remove-Item -Path ".\node_modules" -Recurse -Force
        Write-Host "[SUCCESS] Removed node_modules" -ForegroundColor Green
        Write-Host "[WARNING] Note: Run 'npm install' to reinstall dependencies" -ForegroundColor Yellow
    } else {
        Write-Host "[OK] node_modules not found" -ForegroundColor Green
    }
}
Write-Host ""

Write-Host "=== Cleanup Summary ===" -ForegroundColor Cyan
Write-Host "[SUCCESS] Cleanup completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Cleaned directories:"
Write-Host "  - Python cache (__pycache__, *.pyc)"
Write-Host "  - Test artifacts (.pytest_cache, .coverage)"
Write-Host "  - Build artifacts (dist/, build/)"
Write-Host "  - Log files (logs/*.log)"
Write-Host "  - Temporary files (*.old, *.bak)"
Write-Host "  - OS files (Thumbs.db, desktop.ini)"
Write-Host ""
Write-Host "Ready for deployment!" -ForegroundColor Green

Read-Host -Prompt "Press Enter to exit"
