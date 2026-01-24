###############################################################################
# MBSE Knowledge Graph - Cleanup Script (Windows PowerShell)
# Purpose: Remove temporary files, caches, and build artifacts
# Usage: .\scripts\cleanup.ps1 [-IncludeNodeModules]
###############################################################################

param(
    [switch]$IncludeNodeModules
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "MBSE Knowledge Graph - Cleanup Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..").FullName

Set-Location $ProjectRoot
Write-Host "Project root: $ProjectRoot"
Write-Host ""

function Remove-SafelyLocal {
    param(
        [string]$Path,
        [string]$Description
    )
    
    $fullPath = Join-Path $ProjectRoot $Path
    if (Test-Path $fullPath) {
        Write-Host "Removing: $Description" -ForegroundColor Yellow
        Remove-Item -Path $fullPath -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] Removed: $Path" -ForegroundColor Green
    } else {
        Write-Host "[OK] Already clean: $Description" -ForegroundColor Gray
    }
}

Write-Host "=== Removing Python cache files ===" -ForegroundColor Cyan
Get-ChildItem -Path $ProjectRoot -Directory -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $ProjectRoot -File -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $ProjectRoot -File -Recurse -Filter "*.pyo" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "[OK] Python cache cleaned" -ForegroundColor Green
Write-Host ""

Write-Host "=== Removing test and coverage artifacts ===" -ForegroundColor Cyan
Remove-SafelyLocal -Path ".pytest_cache" -Description "pytest cache"
Remove-SafelyLocal -Path ".coverage" -Description "coverage data"
Remove-SafelyLocal -Path "htmlcov" -Description "HTML coverage report"
Remove-SafelyLocal -Path ".tox" -Description "tox environments"
Write-Host ""

Write-Host "=== Removing build artifacts ===" -ForegroundColor Cyan
Remove-SafelyLocal -Path "build" -Description "build directory"
Remove-SafelyLocal -Path "dist" -Description "distribution directory"
Get-ChildItem -Path $ProjectRoot -Directory -Filter "*.egg-info" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Remove-SafelyLocal -Path ".eggs" -Description "eggs directory"
Write-Host ""

Write-Host "=== Removing Vite/Node cache ===" -ForegroundColor Cyan
Remove-SafelyLocal -Path "node_modules\.cache" -Description "node_modules cache"
Remove-SafelyLocal -Path ".vite" -Description "Vite temp files"
Remove-SafelyLocal -Path "frontend\.vite" -Description "Frontend Vite temp"
Write-Host ""

Write-Host "=== Removing log files ===" -ForegroundColor Cyan
Get-ChildItem -Path (Join-Path $ProjectRoot "logs") -Filter "*.log" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:TEMP\mbse-backend.log" -ErrorAction SilentlyContinue
Remove-Item -Path "$env:TEMP\mbse-backend-error.log" -ErrorAction SilentlyContinue
Remove-Item -Path "$env:TEMP\mbse-frontend.log" -ErrorAction SilentlyContinue
Write-Host "[OK] Log files cleaned" -ForegroundColor Green
Write-Host ""

Write-Host "=== Removing temporary/backup files ===" -ForegroundColor Cyan
Get-ChildItem -Path $ProjectRoot -File -Recurse -Filter "*.old" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $ProjectRoot -File -Recurse -Filter "*.bak" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $ProjectRoot -File -Recurse -Filter "*.swp" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $ProjectRoot -File -Recurse -Filter "Thumbs.db" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "[OK] Temp files cleaned" -ForegroundColor Green
Write-Host ""

if ($IncludeNodeModules) {
    Write-Host "=== Removing node_modules ===" -ForegroundColor Cyan
    Remove-SafelyLocal -Path "node_modules" -Description "node_modules"
    Write-Host "[WARN] Run 'npm install' to reinstall dependencies" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Cleanup complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
