###############################################################################
# MBSE Knowledge Graph - Installation Script (DEPRECATED LOCATION)
# This script has been moved to scripts/install.ps1
# This wrapper forwards to the new location for backward compatibility.
###############################################################################

Write-Host "[NOTE] This script location is deprecated." -ForegroundColor Yellow
Write-Host "       Please use: .\scripts\install.ps1" -ForegroundColor Yellow
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..\..\").FullName
$NewScript = Join-Path $ProjectRoot "scripts\install.ps1"

if (Test-Path $NewScript) {
    & $NewScript @args
    exit $LASTEXITCODE
} else {
    Write-Host "[ERROR] Could not find $NewScript" -ForegroundColor Red
    exit 1
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

# Create Virtual Environment if it doesn't exist
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
    Write-Host "[SUCCESS] Virtual environment created" -ForegroundColor Green
}

$VenvPython = "$InstallDir\.venv\Scripts\python.exe"
$RequirementsFile = "backend\requirements.txt"

if (Test-Path $RequirementsFile) {
    Write-Host "Installing from $RequirementsFile..."
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r $RequirementsFile
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Python dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Some Python dependencies may have failed to install" -ForegroundColor Yellow
    }
} else {
    Write-Host "[WARNING] $RequirementsFile not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Setting up Data ===" -ForegroundColor Cyan

$DataRawDir = "$InstallDir\data\raw"
if (-not (Test-Path $DataRawDir)) {
    New-Item -ItemType Directory -Path $DataRawDir -Force | Out-Null
    Write-Host "[SUCCESS] Created $DataRawDir" -ForegroundColor Green
}

$SourceXmi = "$InstallDir\samples\reference\smrlv12\data\domain_models\mossec\Domain_model.xmi"
$DestXmi = "$DataRawDir\Domain_model.xmi"

if (Test-Path $SourceXmi) {
    Copy-Item -Path $SourceXmi -Destination $DestXmi -Force
    Write-Host "[SUCCESS] Copied Domain_model.xmi to data/raw" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Source XMI not found at $SourceXmi" -ForegroundColor Yellow
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

# Backend (FastAPI)
BACKEND_HOST=0.0.0.0
BACKEND_PORT=5000

# Frontend (Vite)
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=3001

# Frontend dev proxy target (Vite)
API_BASE_URL=http://127.0.0.1:5000

# Legacy compatibility (older templates may still reference these)
# VITE_PORT=3001
# VITE_API_URL=http://127.0.0.1:5000
# API_HOST=0.0.0.0
# API_PORT=5000

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

function Import-DotEnvIfPresent {
    param([string]`$EnvPath)
    if (!(Test-Path -LiteralPath `$EnvPath)) { return }
    Get-Content -LiteralPath `$EnvPath | ForEach-Object {
        `$line = `$_
        if ([string]::IsNullOrWhiteSpace(`$line)) { return }
        `$trimmed = `$line.Trim()
        if (`$trimmed.StartsWith('#')) { return }
        `$idx = `$trimmed.IndexOf('=')
        if (`$idx -lt 1) { return }
        `$key = `$trimmed.Substring(0, `$idx).Trim()
        `$value = `$trimmed.Substring(`$idx + 1).Trim()
        if ([string]::IsNullOrWhiteSpace(`$key)) { return }
        if ((`$value.StartsWith('"') -and `$value.EndsWith('"')) -or (`$value.StartsWith("'") -and `$value.EndsWith("'"))) {
            if (`$value.Length -ge 2) { `$value = `$value.Substring(1, `$value.Length - 2) }
        }
        if ([string]::IsNullOrWhiteSpace([System.Environment]::GetEnvironmentVariable(`$key))) {
            [System.Environment]::SetEnvironmentVariable(`$key, `$value)
        }
    }
}

Import-DotEnvIfPresent -EnvPath (Join-Path "$InstallDir" '.env')

if ([string]::IsNullOrWhiteSpace(`$env:BACKEND_HOST)) { `$env:BACKEND_HOST = '0.0.0.0' }
if ([string]::IsNullOrWhiteSpace(`$env:BACKEND_PORT)) { `$env:BACKEND_PORT = '5000' }
if ([string]::IsNullOrWhiteSpace(`$env:FRONTEND_HOST)) { `$env:FRONTEND_HOST = '0.0.0.0' }
if ([string]::IsNullOrWhiteSpace(`$env:FRONTEND_PORT)) { `$env:FRONTEND_PORT = '3001' }

# Start Backend (in new window)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$InstallDir\backend'; & '$InstallDir\.venv\Scripts\python' -m uvicorn src.web.app_fastapi:app --host $env:BACKEND_HOST --port $env:BACKEND_PORT --reload" -WindowStyle Normal
Start-Sleep -Seconds 3

# Start Frontend (in new window)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$InstallDir'; npm run preview -- --host $env:FRONTEND_HOST --port $env:FRONTEND_PORT" -WindowStyle Normal

Write-Host "Services started!" -ForegroundColor Green
Write-Host "Backend: http://localhost:$env:BACKEND_PORT"
Write-Host "Frontend: http://localhost:$env:FRONTEND_PORT"
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
