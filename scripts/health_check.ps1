###############################################################################
# MBSE Knowledge Graph - Health Check Script (Windows PowerShell)
# Purpose: Validate that the deployment is working correctly
# Usage: .\scripts\health_check.ps1 [-BackendUrl <url>] [-FrontendUrl <url>]
###############################################################################

param(
    [string]$BackendUrl,
    [string]$FrontendUrl
)

function Import-DotEnvIfPresent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EnvPath
    )

    if (-not (Test-Path $EnvPath)) {
        return
    }

    Get-Content $EnvPath | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith('#')) { return }

        $parts = $line -split '=', 2
        if ($parts.Length -ne 2) { return }

        $name = $parts[0].Trim()
        $value = $parts[1].Trim()

        # Remove quotes if present
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        # Force .env to be authoritative
        Set-Item -Path "Env:$name" -Value $value
    }
}

# Load .env from repo root (one level above scripts/)
$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot ".env"
Import-DotEnvIfPresent -EnvPath $envPath

if (-not $BackendUrl) {
    if ($env:API_BASE_URL) {
        $BackendUrl = $env:API_BASE_URL.TrimEnd('/')
    } elseif ($env:BACKEND_HOST -and $env:BACKEND_PORT) {
        # Replace 0.0.0.0 with 127.0.0.1 — 0.0.0.0 is not routable on Windows
        $host_ = if ($env:BACKEND_HOST -eq '0.0.0.0') { '127.0.0.1' } else { $env:BACKEND_HOST }
        $BackendUrl = "http://$($host_):$($env:BACKEND_PORT)"
    } else {
        throw "Missing BackendUrl. Set API_BASE_URL (recommended) or BACKEND_HOST and BACKEND_PORT in .env."
    }
}

if (-not $FrontendUrl) {
    if ($env:FRONTEND_URL) {
        $FrontendUrl = $env:FRONTEND_URL.TrimEnd('/')
    } elseif ($env:FRONTEND_HOST -and $env:FRONTEND_PORT) {
        # Replace 0.0.0.0 with 127.0.0.1 — 0.0.0.0 is not routable on Windows
        $fhost = if ($env:FRONTEND_HOST -eq '0.0.0.0') { '127.0.0.1' } else { $env:FRONTEND_HOST }
        $FrontendUrl = "http://$($fhost):$($env:FRONTEND_PORT)"
    } else {
        throw "Missing FrontendUrl. Set FRONTEND_URL (recommended) or FRONTEND_HOST and FRONTEND_PORT in .env."
    }
}

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
    # FastAPI docs path in this repo is /api/docs.
    $docsOk = $false
    try {
        $response = Invoke-WebRequest -Uri "$BackendUrl/api/docs" -TimeoutSec 10 -ErrorAction Stop
        if ($response.StatusCode -eq 200) { $docsOk = $true }
    } catch {
        # Fallback to older/default docs path
        $response = Invoke-WebRequest -Uri "$BackendUrl/docs" -TimeoutSec 10 -ErrorAction Stop
        if ($response.StatusCode -eq 200) { $docsOk = $true }
    }

    if ($docsOk) {
        Write-Host "      [PASS] API documentation is accessible" -ForegroundColor Green
    } else {
        Write-Host "      [FAIL] API documentation not accessible" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host "      [FAIL] API docs not accessible: $($_.Exception.Message)" -ForegroundColor Red
    $allPassed = $false
}

# Check 3: Graph Data Endpoint
Write-Host "[3/5] Checking Graph Data Endpoint..." -ForegroundColor Yellow
try {
    $headers = @{}
    if ($env:API_KEY) { $headers['X-API-Key'] = $env:API_KEY }
    $response = Invoke-RestMethod -Uri "$BackendUrl/api/graph/node-types" -Headers $headers -TimeoutSec 15 -ErrorAction Stop
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
Write-Host "  API Docs:       $BackendUrl/api/docs"
Write-Host "  Health Check:   $BackendUrl/api/health"
Write-Host ""

if (-not $allPassed) {
    exit 1
}
