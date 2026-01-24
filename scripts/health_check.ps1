###############################################################################
# MBSE Knowledge Graph - Health Check Script (Windows PowerShell)
# Purpose: Validate that the deployment is working correctly
# Usage: .\scripts\health_check.ps1 [-BackendUrl <url>] [-FrontendUrl <url>]
###############################################################################

param(
    [string]$BackendUrl = "http://localhost:5000",
    [string]$FrontendUrl = "http://localhost:3001"
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "MBSE Knowledge Graph - Health Check" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend URL:  $BackendUrl" -ForegroundColor Gray
Write-Host "Frontend URL: $FrontendUrl" -ForegroundColor Gray
Write-Host ""

$allPassed = $true
$warnings = 0

# Check 1: Backend Health Endpoint
Write-Host "[1/5] Checking Backend Health Endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BackendUrl/api/health" -TimeoutSec 10 -ErrorAction Stop
    if ($response.status -eq "healthy" -or $response -match "healthy") {
        Write-Host "      [PASS] Backend is healthy" -ForegroundColor Green
    } else {
        Write-Host "      [WARN] Backend responded but status unclear: $response" -ForegroundColor Yellow
        $warnings++
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
        Write-Host "      [PASS] API documentation is accessible" -ForegroundColor Green
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
        $warnings++
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
        Write-Host "      [PASS] Frontend is accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "      [FAIL] Frontend not accessible: $($_.Exception.Message)" -ForegroundColor Red
    $allPassed = $false
}

# Check 5: Database Connectivity
Write-Host "[5/5] Checking Database Connectivity..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BackendUrl/api/metrics/health" -TimeoutSec 10 -ErrorAction Stop
    if ($response.neo4j -eq "connected" -or $response.database -eq "connected" -or $response.status -eq "healthy") {
        Write-Host "      [PASS] Database connection verified" -ForegroundColor Green
    } else {
        Write-Host "      [WARN] Database status unclear: $($response | ConvertTo-Json -Compress)" -ForegroundColor Yellow
        $warnings++
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
if ($allPassed -and $warnings -eq 0) {
    Write-Host "All checks PASSED! Deployment is healthy." -ForegroundColor Green
} elseif ($allPassed) {
    Write-Host "All checks PASSED with $warnings warning(s)." -ForegroundColor Yellow
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
