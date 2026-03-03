# Start backend + frontend with step-by-step console output.
#
# Prerequisites (start these BEFORE running this script):
#   1. Neo4j        — start via Neo4j Desktop or:  neo4j console  (bolt :7687)
#   2. OpenSearch   — start via:  .\scripts\start_opensearch.ps1 -Detach  (http :9200)
#
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

# --- Prerequisite checks (warn only — do not start Neo4j or OpenSearch) ---
$neo4jUp = $false
try { $null = (New-Object System.Net.Sockets.TcpClient).Connect("127.0.0.1", 7687); $neo4jUp = $true } catch {}

$openSearchUp = $false
try { $r = Invoke-RestMethod "http://localhost:9200" -TimeoutSec 3 -ErrorAction Stop; $openSearchUp = $true } catch {}

if ($neo4jUp) {
    Write-Host "[OK]   Neo4j       is UP on :7687" -ForegroundColor Green
} else {
    Write-Host "[WARN] Neo4j       is NOT running on :7687 — backend will start in degraded mode" -ForegroundColor Yellow
    Write-Host "       Start it first: Neo4j Desktop  -or-  neo4j console" -ForegroundColor DarkYellow
}

if ($openSearchUp) {
    Write-Host "[OK]   OpenSearch  is UP on :9200  (version=$($r.version.number))" -ForegroundColor Green
} else {
    Write-Host "[WARN] OpenSearch  is NOT running on :9200 — RAG/vector search will use fallback" -ForegroundColor Yellow
    Write-Host "       Start it:  .\scripts\start_opensearch.ps1 -Detach" -ForegroundColor DarkYellow
}
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
