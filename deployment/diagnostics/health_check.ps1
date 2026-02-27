###############################################################################
# MBSE Knowledge Graph - Health Check (DEPRECATED LOCATION)
# This script has been moved to scripts/health_check.ps1
# This wrapper forwards to the new location for backward compatibility.
###############################################################################

param(
    [string]$BackendUrl = "http://localhost:5000",
    [string]$FrontendUrl = "http://localhost:3001"
)

Write-Host "[NOTE] This script location is deprecated." -ForegroundColor Yellow
Write-Host "       Please use: .\scripts\health_check.ps1" -ForegroundColor Yellow
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..\..\").FullName
$NewScript = Join-Path $ProjectRoot "scripts\health_check.ps1"

if (Test-Path $NewScript) {
    & $NewScript -BackendUrl $BackendUrl -FrontendUrl $FrontendUrl
    exit $LASTEXITCODE
}

# Fallback to inline execution if new script not found
Write-Host "[WARN] New script not found, running inline..." -ForegroundColor Yellow

$allPassed = $true

# Check 1: Backend Health Endpoint
Write-Host "[1/5] Checking Backend Health Endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BackendUrl/api/health" -TimeoutSec 10 -ErrorAction Stop
    if ($response.status -eq "healthy" -or $response -match "healthy") {
        Write-Host "      [PASS] Backend is healthy" -ForegroundColor Green
    } else {
        Write-Host "      [WARN] Backend responded but status unclear: $response" -ForegroundColor Yellow
    }
} catch {
    Write-Host "      [FAIL] Backend health check failed: $($_.Exception.Message)" -ForegroundColor Red
    $allPassed = $false
}

# Check 2: Backend API Docs
Write-Host "[2/5] Checking Backend API Documentation..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BackendUrl/docs" -TimeoutSec 10 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "      [PASS] API documentation is accessible at $BackendUrl/docs" -ForegroundColor Green
    }
} catch {
    Write-Host "      [FAIL] API docs not accessible: $($_.Exception.Message)" -ForegroundColor Red
    $allPassed = $false
}

# Check 3: Graph Data Endpoint
Write-Host "[3/5] Checking Graph Data Endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BackendUrl/api/graph/node-types" -TimeoutSec 15 -ErrorAction Stop
    $nodeTypes = $response.node_types
    if ($nodeTypes -and $nodeTypes.Count -gt 0) {
        Write-Host "      [PASS] Graph API working - Found $($nodeTypes.Count) node types" -ForegroundColor Green
    } else {
        Write-Host "      [WARN] Graph API responded but no node types found (database may be empty)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "      [FAIL] Graph API check failed: $($_.Exception.Message)" -ForegroundColor Red
    $allPassed = $false
}

# Check 4: Frontend Accessibility
Write-Host "[4/5] Checking Frontend Accessibility..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$FrontendUrl" -TimeoutSec 10 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "      [PASS] Frontend is accessible at $FrontendUrl" -ForegroundColor Green
    }
} catch {
    Write-Host "      [FAIL] Frontend not accessible: $($_.Exception.Message)" -ForegroundColor Red
    $allPassed = $false
}

# Check 5: Neo4j Connectivity (via backend metrics)
Write-Host "[5/5] Checking Database Connectivity..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BackendUrl/api/metrics/health" -TimeoutSec 10 -ErrorAction Stop
    if ($response.neo4j -eq "connected" -or $response.database -eq "connected" -or $response.status -eq "healthy") {
        Write-Host "      [PASS] Database connection verified" -ForegroundColor Green
    } else {
        Write-Host "      [WARN] Database status unclear: $($response | ConvertTo-Json -Compress)" -ForegroundColor Yellow
    }
} catch {
    # Try alternative endpoint
    try {
        $response = Invoke-RestMethod -Uri "$BackendUrl/api/graph/data?limit=1" -TimeoutSec 10 -ErrorAction Stop
        Write-Host "      [PASS] Database connection working (graph query succeeded)" -ForegroundColor Green
    } catch {
        Write-Host "      [FAIL] Database connectivity check failed: $($_.Exception.Message)" -ForegroundColor Red
        $allPassed = $false
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "All checks PASSED! Deployment is healthy." -ForegroundColor Green
} else {
    Write-Host "Some checks FAILED. Review the errors above." -ForegroundColor Red
}
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Endpoints:" -ForegroundColor Yellow
Write-Host "  Frontend UI:    $FrontendUrl"
Write-Host "  Backend API:    $BackendUrl"
Write-Host "  API Docs:       $BackendUrl/docs"
Write-Host "  Health Check:   $BackendUrl/api/health"
Write-Host ""

if (-not $allPassed) {
    exit 1
}
