###############################################################################
# MBSE Knowledge Graph - Installation Script for Windows (PowerShell)
# Purpose: Automated installation on Windows systems
# Usage: .\scripts\install.ps1
# Note: Does NOT require Administrator privileges for standard installation
###############################################################################

param(
    [switch]$SkipNodeInstall,
    [switch]$SkipPythonInstall,
    [string]$InstallDir = $null
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "MBSE Knowledge Graph - Installation" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..").FullName

# If no install dir specified, use current project root (in-place setup)
if (-not $InstallDir) {
    $InstallDir = $ProjectRoot
    Write-Host "Setting up in current directory: $InstallDir" -ForegroundColor Yellow
} else {
    Write-Host "Installation directory: $InstallDir" -ForegroundColor Yellow
}

Set-Location $ProjectRoot

Write-Host ""
Write-Host "=== Checking Prerequisites ===" -ForegroundColor Cyan

# Check Python
$pythonOk = $false
try {
    $pythonVersionOutput = python --version 2>&1
    if ($pythonVersionOutput -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -ge 3 -and $minor -ge 10) {
            Write-Host "[OK] Python found: $pythonVersionOutput" -ForegroundColor Green
            $pythonOk = $true
        } else {
            Write-Host "[WARN] Python version $pythonVersionOutput is below recommended (3.10+)" -ForegroundColor Yellow
            $pythonOk = $true
        }
    }
} catch {
    Write-Host "[ERROR] Python not found. Please install Python 3.10+ from:" -ForegroundColor Red
    Write-Host "        https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "        Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
    exit 1
}

# Check Node.js
$nodeOk = $false
try {
    $nodeVersionOutput = node --version 2>&1
    if ($nodeVersionOutput -match "v(\d+)") {
        $major = [int]$Matches[1]
        if ($major -ge 18) {
            Write-Host "[OK] Node.js found: $nodeVersionOutput" -ForegroundColor Green
            $nodeOk = $true
        } else {
            Write-Host "[WARN] Node.js version $nodeVersionOutput is below recommended (18+)" -ForegroundColor Yellow
            $nodeOk = $true
        }
    }
} catch {
    Write-Host "[ERROR] Node.js not found. Please install Node.js 18+ from:" -ForegroundColor Red
    Write-Host "        https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}

# Check npm
try {
    $npmVersion = npm --version 2>&1
    Write-Host "[OK] npm found: v$npmVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] npm not found. Please reinstall Node.js" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Setting up Python Virtual Environment ===" -ForegroundColor Cyan

Set-Location $InstallDir

# Create Virtual Environment if it doesn't exist
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Virtual environment created" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[OK] Virtual environment already exists" -ForegroundColor Green
}

$VenvPython = Join-Path $InstallDir ".venv\Scripts\python.exe"
$VenvPip = Join-Path $InstallDir ".venv\Scripts\pip.exe"

if (-not $SkipPythonInstall) {
    Write-Host ""
    Write-Host "=== Installing Python Dependencies ===" -ForegroundColor Cyan
    
    $RequirementsFile = Join-Path $InstallDir "backend\requirements.txt"
    
    if (Test-Path $RequirementsFile) {
        Write-Host "Installing from $RequirementsFile..."
        & $VenvPython -m pip install --upgrade pip --quiet
        & $VenvPython -m pip install -r $RequirementsFile
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Python dependencies installed" -ForegroundColor Green
        } else {
            Write-Host "[WARN] Some Python dependencies may have failed to install" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[WARN] $RequirementsFile not found" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== Setting up Data Directory ===" -ForegroundColor Cyan

$DataRawDir = Join-Path $InstallDir "data\raw"
if (-not (Test-Path $DataRawDir)) {
    New-Item -ItemType Directory -Path $DataRawDir -Force | Out-Null
    Write-Host "[OK] Created $DataRawDir" -ForegroundColor Green
} else {
    Write-Host "[OK] $DataRawDir already exists" -ForegroundColor Green
}

# Copy reference XMI if not present
$SourceXmi = Join-Path $InstallDir "samples\reference\smrlv12\data\domain_models\mossec\Domain_model.xmi"
$DestXmi = Join-Path $DataRawDir "Domain_model.xmi"

if ((Test-Path $SourceXmi) -and (-not (Test-Path $DestXmi))) {
    Copy-Item -Path $SourceXmi -Destination $DestXmi -Force
    Write-Host "[OK] Copied Domain_model.xmi to data/raw" -ForegroundColor Green
} elseif (Test-Path $DestXmi) {
    Write-Host "[OK] Domain_model.xmi already present in data/raw" -ForegroundColor Green
}

if (-not $SkipNodeInstall) {
    Write-Host ""
    Write-Host "=== Installing Node.js Dependencies ===" -ForegroundColor Cyan
    
    if (Test-Path (Join-Path $InstallDir "package.json")) {
        Write-Host "Installing Node.js packages..."
        npm install
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Node.js dependencies installed" -ForegroundColor Green
        } else {
            Write-Host "[WARN] Some Node.js dependencies may have failed to install" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[WARN] package.json not found" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "=== Building Frontend Application ===" -ForegroundColor Cyan
    
    npm run build
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Frontend built successfully" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Frontend build had issues (may still work in dev mode)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== Creating Environment Configuration ===" -ForegroundColor Cyan

$EnvFile = Join-Path $InstallDir ".env"
$EnvExample = Join-Path $InstallDir ".env.example"

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item -Path $EnvExample -Destination $EnvFile
        Write-Host "[OK] Created .env from .env.example" -ForegroundColor Green
    } else {
        # Create default .env
        @"
# Neo4j Configuration
NEO4J_URI=neo4j+s://your-neo4j-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# Backend Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=5000

# Frontend Configuration
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=3001
API_BASE_URL=http://localhost:5000

# Logging
LOG_LEVEL=INFO

# Data Directories
DATA_DIR=./data
OUTPUT_DIR=./data/output
"@ | Out-File -FilePath $EnvFile -Encoding UTF8
        Write-Host "[OK] Created default .env file" -ForegroundColor Green
    }
    Write-Host "[ACTION REQUIRED] Edit $EnvFile with your Neo4j credentials" -ForegroundColor Yellow
} else {
    Write-Host "[OK] .env file already exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Configure Neo4j credentials:"
Write-Host "   Edit: $EnvFile"
Write-Host ""
Write-Host "2. Start the services:"
Write-Host "   .\scripts\service_manager.ps1 start"
Write-Host ""
Write-Host "3. Access the application:"
Write-Host "   Frontend UI:  http://localhost:3001"
Write-Host "   Backend API:  http://localhost:5000"
Write-Host "   API Docs:     http://localhost:5000/docs"
Write-Host ""
Write-Host "4. Run health check:"
Write-Host "   .\scripts\health_check.ps1"
Write-Host ""
Write-Host "For help with scripts:"
Write-Host "   .\scripts\service_manager.ps1 help"
Write-Host ""
