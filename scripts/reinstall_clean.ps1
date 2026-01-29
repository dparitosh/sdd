<#
.SYNOPSIS
  Clean re-clone + reinstall + start services on Windows.

.DESCRIPTION
  This script helps you:
    1) Back up an existing .env
    2) Delete an old checkout folder
    3) Fresh clone this repo
    4) Checkout a branch
    5) Restore .env
    6) Run install.ps1
    7) Start services via service_manager.ps1

  You must have Git, Node, and Python installed.

.PARAMETER OldPath
  Path to the old checkout folder to remove (e.g. C:\MBSE\mbse-neo4j-graph-rep)

.PARAMETER ParentPath
  Directory where the new clone will be created (e.g. C:\MBSE)

.PARAMETER Branch
  Branch to checkout after clone (default: chore/audit-cleanup)

.PARAMETER RepoUrl
  Git URL to clone.

.PARAMETER SkipStart
  If set, performs reinstall but does not start services.

.EXAMPLE
  .\scripts\reinstall_clean.ps1 -OldPath C:\MBSE\mbse-neo4j-graph-rep -ParentPath C:\MBSE
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OldPath,

    [Parameter(Mandatory = $true)]
    [string]$ParentPath,

    [string]$Branch = 'chore/audit-cleanup',

    [string]$RepoUrl = 'https://github.com/dparitosh/mbse-neo4j-graph-rep.git',

    [switch]$SkipStart
)

$ErrorActionPreference = 'Stop'

function Require-Command([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Required command not found on PATH: $Name"
    }
}

Require-Command git
Require-Command node
Require-Command npm
Require-Command python

if (-not (Test-Path -LiteralPath $ParentPath)) {
  Write-Host "ParentPath does not exist; creating: $ParentPath" -ForegroundColor Yellow
  New-Item -ItemType Directory -Path $ParentPath -Force | Out-Null
}

$ParentPath = (Resolve-Path -LiteralPath $ParentPath).Path

# OldPath may or may not exist. If it exists, resolve it for safety.
if (Test-Path -LiteralPath $OldPath) {
  $OldPath = (Resolve-Path -LiteralPath $OldPath).Path
}

$backupDir = Join-Path $env:TEMP ("mbse-backup-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

$oldEnv = Join-Path $OldPath '.env'
$envBackup = $null
if ($OldPath -and (Test-Path -LiteralPath $oldEnv)) {
    $envBackup = Join-Path $backupDir '.env'
    Copy-Item -LiteralPath $oldEnv -Destination $envBackup -Force
    Write-Host "Backed up .env to $envBackup" -ForegroundColor Green
} else {
    Write-Host "No .env found at $oldEnv (skipping backup)" -ForegroundColor Yellow
}

Write-Host "Removing old checkout: $OldPath" -ForegroundColor Yellow
if ($OldPath -and (Test-Path -LiteralPath $OldPath)) {
  Remove-Item -LiteralPath $OldPath -Recurse -Force
} else {
  Write-Host "OldPath does not exist; skipping delete." -ForegroundColor DarkGray
}

Write-Host "Cloning repo into: $ParentPath" -ForegroundColor Cyan
Set-Location $ParentPath

git clone $RepoUrl

$newPath = Join-Path $ParentPath 'mbse-neo4j-graph-rep'
Set-Location $newPath

git checkout $Branch

if ($envBackup -and (Test-Path -LiteralPath $envBackup)) {
    Copy-Item -LiteralPath $envBackup -Destination (Join-Path $newPath '.env') -Force
    Write-Host "Restored .env" -ForegroundColor Green
}

Write-Host "Running installer..." -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1

if (-not $SkipStart) {
    Write-Host "Starting services (interactive)..." -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\service_manager.ps1 start -Interactive -Inspect
} else {
    Write-Host "Reinstall complete. (SkipStart specified; not starting services.)" -ForegroundColor Green
}
