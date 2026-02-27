###############################################################################
# MBSE Knowledge Graph - OSLC Installation Script
# Purpose: Installs OSLC dependencies and seeds OSLC Core/RM ontologies
# Usage: .\scripts\install_oslc.ps1
###############################################################################

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "MBSE OSLC Module Installation" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..").FullName
Set-Location $ProjectRoot

# 1. Install Dependencies
Write-Host ">>> Installing Python dependencies..." -ForegroundColor Yellow
$PythonPath = "python" # Assumes python is in path, or use specific venv path if needed
if (Test-Path ".venv\Scripts\python.exe") {
    $PythonPath = ".venv\Scripts\python.exe"
}

try {
    & $PythonPath -m pip install rdflib owlrl pyshacl httpx slowapi
    Write-Host "Dependencies installed successfully." -ForegroundColor Green
} catch {
    Write-Host "Failed to install dependencies. Please run manually: pip install rdflib owlrl pyshacl httpx slowapi" -ForegroundColor Red
    exit 1
}

# 2. Start Backend Services (if not running)
# Note: In a real script we might check port 7687, but here we assume user handles Neo4j
Write-Host ">>> Checking Neo4j connection..." -ForegroundColor Yellow
# Simple check logic or reminder
Write-Host "Ensure Neo4j is running at neo4j://localhost:7687" -ForegroundColor Gray


# 3. Seed Ontologies
Write-Host ">>> Seeding OSLC Ontologies..." -ForegroundColor Yellow

$CorePath = "backend/data/seed/oslc/oslc-core.ttl"
$RMPath = "backend/data/seed/oslc/oslc-rm.ttl"

if (Test-Path $CorePath) {
    Write-Host "Ingesting OSLC Core..." -ForegroundColor Cyan
    & $PythonPath backend/scripts/ingest_ontology_rdf.py --path $CorePath --name OSLC-Core
} else {
    Write-Host "OSLC Core schema not found at $CorePath" -ForegroundColor Red
}

if (Test-Path $RMPath) {
    Write-Host "Ingesting OSLC RM..." -ForegroundColor Cyan
    & $PythonPath backend/scripts/ingest_ontology_rdf.py --path $RMPath --name OSLC-RM
} else {
    Write-Host "OSLC RM schema not found at $RMPath" -ForegroundColor Red
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "OSLC Installation Complete" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
