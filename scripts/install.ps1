###############################################################################
# MBSE Knowledge Graph - Installation Script for Windows (PowerShell)
# Purpose: Automated installation on Windows systems
# Usage: .\scripts\install.ps1
# Note: Does NOT require Administrator privileges for standard installation
###############################################################################

param(
    [switch]$SkipNodeInstall,
    [switch]$SkipPythonInstall,
    [string]$InstallDir = $null,

    # If set, the installer will fail fast when Neo4j credentials are missing/placeholder.
    # If not set (default), it will warn and let you proceed (useful for installing before you have Aura details).
    [switch]$RequireNeo4j
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

function Import-DotEnvIfPresent {
    param(
        [Parameter(Mandatory=$true)]
        [string]$EnvPath
    )

    if (!(Test-Path -LiteralPath $EnvPath)) {
        return
    }

    Get-Content -LiteralPath $EnvPath | ForEach-Object {
        $line = $_
        if ([string]::IsNullOrWhiteSpace($line)) { return }
        $trimmed = $line.Trim()
        if ($trimmed.StartsWith('#')) { return }

        $idx = $trimmed.IndexOf('=')
        if ($idx -lt 1) { return }

        $key = $trimmed.Substring(0, $idx).Trim()
        $value = $trimmed.Substring($idx + 1).Trim()
        if ([string]::IsNullOrWhiteSpace($key)) { return }

        # Remove surrounding quotes
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            if ($value.Length -ge 2) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }

        # Don't override explicitly-set env vars
        if ([string]::IsNullOrWhiteSpace([System.Environment]::GetEnvironmentVariable($key))) {
            [System.Environment]::SetEnvironmentVariable($key, $value)
        }
    }
}

function Is-PlaceholderNeo4jValue {
    param(
        [AllowNull()]
        [string]$Value
    )
    if ([string]::IsNullOrWhiteSpace($Value)) { return $true }

    $v = $Value.Trim().ToLowerInvariant()
    # Common placeholder patterns used in templates
    if ($v -match 'your-neo4j' -or $v -match '<your-' -or $v -match 'changeme' -or $v -match 'your-password') { return $true }
    return $false
}

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
API_BASE_URL=http://127.0.0.1:5000

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

# Load env vars from .env now so later steps (like frontend build / checks) can rely on them.
Import-DotEnvIfPresent -EnvPath $EnvFile

# Neo4j credentials sanity check (no secrets printed)
$neo4jMissing = @()
foreach ($name in @('NEO4J_URI','NEO4J_USER','NEO4J_PASSWORD')) {
    if ([string]::IsNullOrWhiteSpace([System.Environment]::GetEnvironmentVariable($name))) {
        $neo4jMissing += $name
    }
}

$neo4jUriPlaceholder = Is-PlaceholderNeo4jValue -Value $env:NEO4J_URI
$neo4jUserPlaceholder = Is-PlaceholderNeo4jValue -Value $env:NEO4J_USER
$neo4jPassPlaceholder = Is-PlaceholderNeo4jValue -Value $env:NEO4J_PASSWORD

if ($neo4jMissing.Count -gt 0 -or $neo4jUriPlaceholder -or $neo4jUserPlaceholder -or $neo4jPassPlaceholder) {
    $msg = "Neo4j connection details are not configured (missing/placeholder). Edit $EnvFile (see .env.example)."
    if ($RequireNeo4j) {
        Write-Host "[ERROR] $msg" -ForegroundColor Red
        exit 1
    } else {
        Write-Host "[WARN] $msg" -ForegroundColor Yellow
        Write-Host "       Installer will continue, but backend will not be able to connect until you set real credentials." -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] Neo4j credentials appear to be set (value check only; connectivity will be verified after Python deps install)" -ForegroundColor Green
}

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

        # If Neo4j creds look real, verify connectivity now (fail early)
        if (-not (Is-PlaceholderNeo4jValue -Value $env:NEO4J_URI) -and -not (Is-PlaceholderNeo4jValue -Value $env:NEO4J_USER) -and -not (Is-PlaceholderNeo4jValue -Value $env:NEO4J_PASSWORD)) {
            Write-Host "" 
            Write-Host "=== Verifying Neo4j Connectivity ===" -ForegroundColor Cyan
            & $VenvPython (Join-Path $InstallDir "scripts\verify_connectivity.py")
            if ($LASTEXITCODE -ne 0) {
                $msg2 = "Neo4j connectivity check failed. Fix NEO4J_* in .env and rerun: .\\.venv\\Scripts\\python.exe scripts\\verify_connectivity.py"
                if ($RequireNeo4j) {
                    Write-Host "[ERROR] $msg2" -ForegroundColor Red
                    exit 1
                } else {
                    Write-Host "[WARN] $msg2" -ForegroundColor Yellow
                }
            } else {
                Write-Host "[OK] Neo4j connectivity verified" -ForegroundColor Green
            }
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
$candidateXmiPaths = @(
    (Join-Path $InstallDir "smrlv12\data\domain_models\mossec\Domain_model.xmi"),
    (Join-Path $InstallDir "samples\reference\smrlv12\data\domain_models\mossec\Domain_model.xmi")
)

$SourceXmi = $null
foreach ($candidate in $candidateXmiPaths) {
    if (Test-Path $candidate) {
        $SourceXmi = $candidate
        break
    }
}
$DestXmi = Join-Path $DataRawDir "Domain_model.xmi"

if ($SourceXmi -and (-not (Test-Path $DestXmi))) {
    Copy-Item -Path $SourceXmi -Destination $DestXmi -Force
    Write-Host "[OK] Copied Domain_model.xmi to data/raw" -ForegroundColor Green
} elseif (Test-Path $DestXmi) {
    Write-Host "[OK] Domain_model.xmi already present in data/raw" -ForegroundColor Green
} else {
    Write-Host "[WARN] Reference Domain_model.xmi not found to copy into data/raw." -ForegroundColor Yellow
    Write-Host "       You can still run with your own XMI files in data/raw/, or use smrlv12 reference data." -ForegroundColor Yellow
}

if (-not $SkipNodeInstall) {
    Write-Host ""
    Write-Host "=== Installing Node.js Dependencies ===" -ForegroundColor Cyan
    
    if (Test-Path (Join-Path $InstallDir "package.json")) {
        Write-Host "Installing Node.js packages..."

        # Guardrail: if a stale lockfile pins incompatible React versions (e.g., React 19)
        # it can trigger peer-dependency failures even though package.json has been updated.
        $lockPath = Join-Path $InstallDir "package-lock.json"
        if (Test-Path -LiteralPath $lockPath) {
            try {
                $lockHasReact19 = Select-String -LiteralPath $lockPath -Pattern '"react"\s*:\s*"\^19\.|react@19\.' -Quiet
                if ($lockHasReact19) {
                    Write-Host "[WARN] Detected stale package-lock.json referencing React 19. Removing lockfile to allow a clean install." -ForegroundColor Yellow
                    Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue

                    $nmPath = Join-Path $InstallDir "node_modules"
                    if (Test-Path -LiteralPath $nmPath) {
                        Write-Host "[INFO] Removing existing node_modules for a clean dependency install..." -ForegroundColor DarkGray
                        Remove-Item -LiteralPath $nmPath -Recurse -Force -ErrorAction SilentlyContinue
                    }
                }
            } catch {
                # If lockfile can't be inspected, proceed without blocking install.
            }
        }

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
$frontendPortForDisplay = if (-not [string]::IsNullOrWhiteSpace($env:FRONTEND_PORT)) { $env:FRONTEND_PORT } else { "3001" }
$backendBaseUrlForDisplay = if (-not [string]::IsNullOrWhiteSpace($env:API_BASE_URL)) { $env:API_BASE_URL.TrimEnd('/') } else { "" }

Write-Host "   Frontend UI:  http://localhost:$frontendPortForDisplay"
if (-not [string]::IsNullOrWhiteSpace($backendBaseUrlForDisplay)) {
    Write-Host "   Backend API:  $backendBaseUrlForDisplay"
    Write-Host "   API Docs:     $backendBaseUrlForDisplay/docs"
} else {
    Write-Host "   Backend API:  (set API_BASE_URL in .env)" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "4. Run health check:"
Write-Host "   .\scripts\health_check.ps1"
Write-Host ""
Write-Host "For help with scripts:"
Write-Host "   .\scripts\service_manager.ps1 help"
Write-Host ""
