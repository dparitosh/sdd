###############################################################################
# MBSE Knowledge Graph - Clean Reinstall Script (Windows PowerShell)
# Purpose: Stop services, clean local dependencies, reinstall, and (optionally) start.
# Usage:
#   .\scripts\reinstall.ps1
#   .\scripts\reinstall.ps1 -Start
#   .\scripts\reinstall.ps1 -BackupEnv
#   .\scripts\reinstall.ps1 -BackupEnv -BackupData -Start
###############################################################################

param(
    # Back up .env to a timestamped file in the repo root.
    [switch]$BackupEnv,

    # Back up ./data to a timestamped folder in the repo root.
    [switch]$BackupData,

    # If set, starts services after reinstall.
    [switch]$Start,

    # If set, also deletes node_modules even if lockfile doesn't look stale.
    [switch]$ForceNodeModulesClean
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..").FullName

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "MBSE Knowledge Graph - Clean Reinstall" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot" -ForegroundColor DarkGray

Set-Location $ProjectRoot

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

# Stop running services (best-effort)
try {
    Write-Host "[INFO] Stopping services (best-effort)..." -ForegroundColor DarkGray
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "scripts\service_manager.ps1") stop | Out-Null
} catch {
    # ignore
}

# Backups
if ($BackupEnv) {
    $envPath = Join-Path $ProjectRoot ".env"
    if (Test-Path -LiteralPath $envPath) {
        $dest = Join-Path $ProjectRoot (".env.backup." + $timestamp)
        Copy-Item -LiteralPath $envPath -Destination $dest -Force
        Write-Host "[OK] Backed up .env -> $dest" -ForegroundColor Green
    } else {
        Write-Host "[WARN] No .env found to back up" -ForegroundColor Yellow
    }
}

if ($BackupData) {
    $dataPath = Join-Path $ProjectRoot "data"
    if (Test-Path -LiteralPath $dataPath) {
        $dest = Join-Path $ProjectRoot ("data.backup." + $timestamp)
        Copy-Item -LiteralPath $dataPath -Destination $dest -Recurse -Force
        Write-Host "[OK] Backed up data -> $dest" -ForegroundColor Green
    } else {
        Write-Host "[WARN] No data folder found to back up" -ForegroundColor Yellow
    }
}

# Clean Python env
$venvPath = Join-Path $ProjectRoot ".venv"
if (Test-Path -LiteralPath $venvPath) {
    Write-Host "[INFO] Removing .venv..." -ForegroundColor DarkGray
    Remove-Item -LiteralPath $venvPath -Recurse -Force -ErrorAction SilentlyContinue
}

# Clean frontend build output
$distPath = Join-Path $ProjectRoot "dist"
if (Test-Path -LiteralPath $distPath) {
    Write-Host "[INFO] Removing dist/..." -ForegroundColor DarkGray
    Remove-Item -LiteralPath $distPath -Recurse -Force -ErrorAction SilentlyContinue
}

# Clean node deps
$lockPath = Join-Path $ProjectRoot "package-lock.json"
$nodeModulesPath = Join-Path $ProjectRoot "node_modules"

$lockHasReact19 = $false
if (Test-Path -LiteralPath $lockPath) {
    try {
        $lockHasReact19 = Select-String -LiteralPath $lockPath -Pattern '"react"\s*:\s*"\^19\.|react@19\.' -Quiet
    } catch {
        $lockHasReact19 = $false
    }
}

if ($lockHasReact19) {
    Write-Host "[WARN] Detected package-lock.json referencing React 19; removing lockfile for a clean install." -ForegroundColor Yellow
    Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
}

if ($ForceNodeModulesClean -or $lockHasReact19) {
    if (Test-Path -LiteralPath $nodeModulesPath) {
        Write-Host "[INFO] Removing node_modules/..." -ForegroundColor DarkGray
        Remove-Item -LiteralPath $nodeModulesPath -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Reinstall using the main installer
Write-Host "[INFO] Running installer..." -ForegroundColor DarkGray
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "scripts\install.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Installer exited with code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

if ($Start) {
    Write-Host "[INFO] Starting services..." -ForegroundColor DarkGray
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "scripts\service_manager.ps1") start -Interactive -Inspect
}

Write-Host "[OK] Clean reinstall complete." -ForegroundColor Green
