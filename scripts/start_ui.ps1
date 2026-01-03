# Start Vite frontend from repo root (Windows PowerShell)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

Write-Host "=================================="
Write-Host "Starting MBSE Knowledge Graph UI"
Write-Host "=================================="
Write-Host ""

$nodeModules = Join-Path $repoRoot "node_modules"
if (!(Test-Path $nodeModules)) {
    Write-Host "Installing dependencies..."
    npm install
}

npm run dev
