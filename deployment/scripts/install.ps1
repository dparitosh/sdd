###############################################################################
# MBSE Knowledge Graph - Installation Script for Windows (PowerShell)
# Purpose: Automated installation on Windows systems
# Usage: .\install.ps1 (Run as Administrator)
# Note: This script requires Administrator privileges
###############################################################################

#Requires -RunAsAdministrator

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "MBSE Knowledge Graph - Installation" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$PythonVersion = "3.12"
$NodeVersion = "20"
$InstallDir = "C:\MBSE\mbse-neo4j-graph-rep"
$LogDir = "C:\MBSE\logs"

Write-Host "This script will install:" -ForegroundColor Yellow
Write-Host "  - Python $PythonVersion and dependencies"
Write-Host "  - Node.js $NodeVersion and npm"
Write-Host "  - MBSE Knowledge Graph application"
Write-Host ""

$response = Read-Host "Continue with installation? (y/N)"
if ($response -ne 'y' -and $response -ne 'Y') {
    Write-Host "Installation cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "=== Checking Prerequisites ===" -ForegroundColor Cyan

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[SUCCESS] Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found. Please install Python $PythonVersion from:" -ForegroundColor Red
    Write-Host "https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Node.js
try {
    $nodeVersion = node --version 2>&1
    Write-Host "[SUCCESS] Node.js found: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Node.js not found. Please install Node.js $NodeVersion from:" -ForegroundColor Red
    Write-Host "https://nodejs.org/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check npm
try {
    $npmVersion = npm --version 2>&1
    Write-Host "[SUCCESS] npm found: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] npm not found. Please reinstall Node.js" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "=== Creating Installation Directories ===" -ForegroundColor Cyan

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    Write-Host "[SUCCESS] Created $InstallDir" -ForegroundColor Green
} else {
    Write-Host "[WARNING] $InstallDir already exists" -ForegroundColor Yellow
}

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    Write-Host "[SUCCESS] Created $LogDir" -ForegroundColor Green
} else {
    Write-Host "[OK] $LogDir already exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Copying Application Files ===" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..\..\").FullName

Write-Host "Copying from: $ProjectRoot"
Write-Host "Copying to: $InstallDir"

$ExcludeDirs = @('node_modules', '__pycache__', '.git', '.pytest_cache', 'htmlcov', 'dist', '.vscode')
$ExcludeFiles = @('*.pyc', '*.pyo', '*.log', '.coverage')

try {
    Get-ChildItem -Path $ProjectRoot -Recurse -Exclude $ExcludeFiles | 
        Where-Object { 
            $exclude = $false
            foreach ($dir in $ExcludeDirs) {
                if ($_.FullName -like "*\$dir\*" -or $_.Name -eq $dir) {
                    $exclude = $true
                    break
                }
            }
            -not $exclude
        } |
        ForEach-Object {
            $targetPath = $_.FullName.Replace($ProjectRoot, $InstallDir)
            if ($_.PSIsContainer) {
                if (-not (Test-Path $targetPath)) {
                    New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
                }
            } else {
                $targetDir = Split-Path -Parent $targetPath
                if (-not (Test-Path $targetDir)) {
                    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
                }
                Copy-Item $_.FullName -Destination $targetPath -Force
            }
        }
    Write-Host "[SUCCESS] Application files copied" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Some files may not have been copied: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Installing Python Dependencies ===" -ForegroundColor Cyan

Set-Location $InstallDir

if (Test-Path "requirements.txt") {
    Write-Host "Installing from requirements.txt..."
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Python dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Some Python dependencies may have failed to install" -ForegroundColor Yellow
    }
} else {
    Write-Host "[WARNING] requirements.txt not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Installing Node.js Dependencies ===" -ForegroundColor Cyan

if (Test-Path "package.json") {
    Write-Host "Installing Node.js packages..."
    npm install
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Node.js dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Some Node.js dependencies may have failed to install" -ForegroundColor Yellow
    }
} else {
    Write-Host "[WARNING] package.json not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Building Frontend Application ===" -ForegroundColor Cyan

npm run build
if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] Frontend built successfully" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Frontend build failed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Creating Environment Configuration ===" -ForegroundColor Cyan

if (-not (Test-Path "$InstallDir\.env")) {
    Write-Host "Creating .env file..."
    @"
# Neo4j Configuration
NEO4J_URI=neo4j+s://your-neo4j-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# API Configuration
API_HOST=0.0.0.0
API_PORT=5000

# Frontend Configuration
VITE_PORT=3001
VITE_API_URL=http://localhost:5000

# Logging
LOG_LEVEL=INFO
"@ | Out-File -FilePath "$InstallDir\.env" -Encoding UTF8
    Write-Host "[SUCCESS] Environment file created" -ForegroundColor Green
    Write-Host "[WARNING] Please edit $InstallDir\.env with your settings" -ForegroundColor Yellow
} else {
    Write-Host "[OK] Environment file already exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Creating Service Scripts ===" -ForegroundColor Cyan

# Create start_all.ps1
@"
Write-Host "Starting MBSE Knowledge Graph services..." -ForegroundColor Cyan
Set-Location "$InstallDir"
`$env:PYTHONPATH = "$InstallDir"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$InstallDir'; `$env:PYTHONPATH='$InstallDir'; python -m uvicorn src.web.app_fastapi:app --host 0.0.0.0 --port 5000" -WindowStyle Normal
Start-Sleep -Seconds 3
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$InstallDir'; npm run preview -- --host 0.0.0.0 --port 3001" -WindowStyle Normal

Write-Host "Services started!" -ForegroundColor Green
Write-Host "Backend: http://localhost:5000"
Write-Host "Frontend: http://localhost:3001"
"@ | Out-File -FilePath "$InstallDir\start_all.ps1" -Encoding UTF8
Write-Host "[SUCCESS] Created start_all.ps1" -ForegroundColor Green

# Create stop_all.ps1
@"
Write-Host "Stopping MBSE Knowledge Graph services..." -ForegroundColor Cyan
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { `$_.Path -like "*$InstallDir*" } | Stop-Process -Force
Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object { `$_.Path -like "*$InstallDir*" } | Stop-Process -Force
Write-Host "Services stopped!" -ForegroundColor Green
"@ | Out-File -FilePath "$InstallDir\stop_all.ps1" -Encoding UTF8
Write-Host "[SUCCESS] Created stop_all.ps1" -ForegroundColor Green

Write-Host ""
Write-Host "=== Installation Complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Configure environment variables:"
Write-Host "   Edit: $InstallDir\.env"
Write-Host ""
Write-Host "2. Start the services:"
Write-Host "   Run: $InstallDir\start_all.ps1"
Write-Host ""
Write-Host "3. Access the application:"
Write-Host "   Frontend UI: http://localhost:3001"
Write-Host "   Backend API: http://localhost:5000"
Write-Host "   Health Check: http://localhost:5000/api/health"
Write-Host ""
Write-Host "Installation location: $InstallDir" -ForegroundColor Cyan
Write-Host "Logs location: $LogDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "For service management, use:" -ForegroundColor Yellow
Write-Host "   $InstallDir\deployment\scripts\service_manager.ps1"
Write-Host ""

Read-Host "Press Enter to exit"
