@echo off
REM ###############################################################################
REM MBSE Knowledge Graph - Installation Script for Windows
REM Purpose: Automated installation on Windows systems
REM Usage: install.bat (Run as Administrator)
REM Note: This script requires Administrator privileges
REM ###############################################################################

setlocal enabledelayedexpansion

REM Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script must be run as Administrator!
    echo Right-click this file and select "Run as Administrator"
    pause
    exit /b 1
)

echo ==========================================
echo MBSE Knowledge Graph - Installation
echo ==========================================
echo.

set "PYTHON_VERSION=3.12"
set "NODE_VERSION=20"
set "INSTALL_DIR=C:\MBSE\mbse-neo4j-graph-rep"
set "LOG_DIR=C:\MBSE\logs"

echo This script will install:
echo   - Python %PYTHON_VERSION% and dependencies
echo   - Node.js %NODE_VERSION% and npm
echo   - MBSE Knowledge Graph application
echo.
set /p REPLY="Continue with installation? (y/N): "
if /i not "%REPLY%"=="y" (
    echo Installation cancelled.
    exit /b 0
)

echo.
echo === Checking Prerequisites ===

REM Check if Python is installed
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARNING] Python not found. Please install Python %PYTHON_VERSION% from:
    echo https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%v in ('python --version') do set CURRENT_PYTHON=%%v
    echo [SUCCESS] Python found: !CURRENT_PYTHON!
)

REM Check if Node.js is installed
node --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARNING] Node.js not found. Please install Node.js %NODE_VERSION% from:
    echo https://nodejs.org/
    pause
    exit /b 1
) else (
    for /f "tokens=1" %%v in ('node --version') do set CURRENT_NODE=%%v
    echo [SUCCESS] Node.js found: !CURRENT_NODE!
)

REM Check if npm is installed
npm --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] npm not found. Please reinstall Node.js
    pause
    exit /b 1
) else (
    for /f "tokens=1" %%v in ('npm --version') do set CURRENT_NPM=%%v
    echo [SUCCESS] npm found: !CURRENT_NPM!
)

echo.
echo === Creating Installation Directories ===
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    echo [SUCCESS] Created %INSTALL_DIR%
) else (
    echo [WARNING] %INSTALL_DIR% already exists
)

if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
    echo [SUCCESS] Created %LOG_DIR%
) else (
    echo [OK] %LOG_DIR% already exists
)

echo.
echo === Copying Application Files ===
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."

echo Copying from: %PROJECT_ROOT%
echo Copying to: %INSTALL_DIR%

xcopy /E /I /Y /EXCLUDE:%SCRIPT_DIR%exclude.txt "%PROJECT_ROOT%" "%INSTALL_DIR%" >nul 2>&1
if %errorLevel% equ 0 (
    echo [SUCCESS] Application files copied
) else (
    REM Fallback if exclude.txt doesn't exist
    xcopy /E /I /Y "%PROJECT_ROOT%\backend" "%INSTALL_DIR%\backend" >nul 2>&1
    xcopy /E /I /Y "%PROJECT_ROOT%\frontend" "%INSTALL_DIR%\frontend" >nul 2>&1
    xcopy /E /I /Y "%PROJECT_ROOT%\deployment" "%INSTALL_DIR%\deployment" >nul 2>&1
    xcopy /E /I /Y "%PROJECT_ROOT%\samples" "%INSTALL_DIR%\samples" >nul 2>&1
    xcopy /Y "%PROJECT_ROOT%\package.json" "%INSTALL_DIR%" >nul 2>&1
    xcopy /Y "%PROJECT_ROOT%\*.md" "%INSTALL_DIR%" >nul 2>&1
    xcopy /Y "%PROJECT_ROOT%\*.json" "%INSTALL_DIR%" >nul 2>&1
    xcopy /Y "%PROJECT_ROOT%\*.js" "%INSTALL_DIR%" >nul 2>&1
    echo [SUCCESS] Application files copied (basic)
)

echo.
echo === Installing Python Dependencies ===
cd /d "%INSTALL_DIR%"

if exist "backend\requirements.txt" (
    echo Installing from backend\requirements.txt...
    python -m pip install --upgrade pip
    python -m pip install -r backend\requirements.txt
    if %errorLevel% equ 0 (
        echo [SUCCESS] Python dependencies installed
    ) else (
        echo [WARNING] Some Python dependencies may have failed to install
    )
) else (
    echo [WARNING] backend\requirements.txt not found
)

echo.
echo === Setting up Data ===
if not exist "%INSTALL_DIR%\data\raw" (
    mkdir "%INSTALL_DIR%\data\raw"
    echo [SUCCESS] Created data\raw
)

if exist "%INSTALL_DIR%\samples\reference\smrlv12\data\domain_models\mossec\Domain_model.xmi" (
    copy /Y "%INSTALL_DIR%\samples\reference\smrlv12\data\domain_models\mossec\Domain_model.xmi" "%INSTALL_DIR%\data\raw\Domain_model.xmi" >nul
    echo [SUCCESS] Copied Domain_model.xmi to data\raw
) else (
    echo [WARNING] Domain_model.xmi not found
)

echo.
echo === Installing Node.js Dependencies ===
if exist "package.json" (
    echo Installing Node.js packages...
    call npm install
    if %errorLevel% equ 0 (
        echo [SUCCESS] Node.js dependencies installed
    ) else (
        echo [WARNING] Some Node.js dependencies may have failed to install
    )
) else (
    echo [WARNING] package.json not found
)

echo.
echo === Building Frontend Application ===
call npm run build
if %errorLevel% equ 0 (
    echo [SUCCESS] Frontend built successfully
) else (
    echo [WARNING] Frontend build failed
)

echo.
echo === Creating Environment Configuration ===
if not exist "%INSTALL_DIR%\.env" (
    echo Creating .env file...
    (
        echo # Neo4j Configuration
        echo NEO4J_URI=neo4j+s://your-neo4j-instance.databases.neo4j.io
        echo NEO4J_USER=neo4j
        echo NEO4J_PASSWORD=your-password
        echo NEO4J_DATABASE=neo4j
        echo.
        echo # Backend ^(FastAPI^)
        echo BACKEND_HOST=0.0.0.0
        echo BACKEND_PORT=5000
        echo.
        echo # Frontend ^(Vite^)
        echo FRONTEND_HOST=0.0.0.0
        echo FRONTEND_PORT=3001
        echo.
        echo # Frontend dev proxy target ^(Vite^)
        echo API_BASE_URL=http://127.0.0.1:5000
        echo.
        echo # Legacy compatibility ^(older templates may still reference these^)
        echo REM VITE_PORT=3001
        echo REM VITE_API_URL=http://127.0.0.1:5000
        echo REM API_HOST=0.0.0.0
        echo REM API_PORT=5000
        echo.
        echo # Logging
        echo LOG_LEVEL=INFO
    ) > "%INSTALL_DIR%\.env"
    echo [SUCCESS] Environment file created
    echo [WARNING] Please edit %INSTALL_DIR%\.env with your settings
) else (
    echo [OK] Environment file already exists
)

echo.
echo === Creating Service Scripts ===

REM Create start_all.bat
(
    echo @echo off
    echo echo Starting MBSE Knowledge Graph services...
    echo cd /d "%INSTALL_DIR%"
    echo REM NOTE: Ports/hosts are controlled via .env ^(BACKEND_HOST/BACKEND_PORT, FRONTEND_HOST/FRONTEND_PORT^)
    echo start "MBSE Backend" cmd /k "cd backend && python -m uvicorn src.web.app_fastapi:app --host 0.0.0.0 --port 5000"
    echo timeout /t 3 /nobreak ^>nul
    echo start "MBSE Frontend" cmd /k "npm run preview -- --host 0.0.0.0 --port 3001"
    echo echo Services started!
    echo echo Backend: http://localhost:5000
    echo echo Frontend: http://localhost:3001
    echo pause
) > "%INSTALL_DIR%\start_all.bat"
echo [SUCCESS] Created start_all.bat

REM Create stop_all.bat
(
    echo @echo off
    echo echo Stopping MBSE Knowledge Graph services...
    echo taskkill /F /FI "WINDOWTITLE eq MBSE Backend*" /T ^>nul 2^>^&1
    echo taskkill /F /FI "WINDOWTITLE eq MBSE Frontend*" /T ^>nul 2^>^&1
    echo REM Avoid killing arbitrary python.exe; stop by PID when possible.
    echo echo Services stopped!
    echo pause
) > "%INSTALL_DIR%\stop_all.bat"
echo [SUCCESS] Created stop_all.bat

echo.
echo === Installation Complete! ===
echo.
echo Next Steps:
echo.
echo 1. Configure environment variables:
echo    Edit: %INSTALL_DIR%\.env
echo.
echo 2. Start the services:
echo    Run: %INSTALL_DIR%\start_all.bat
echo.
echo 3. Access the application:
echo    Frontend UI: http://localhost:3001
echo    Backend API: http://localhost:5000
echo    Health Check: http://localhost:5000/api/health
echo.
echo Installation location: %INSTALL_DIR%
echo Logs location: %LOG_DIR%
echo.
echo For service management, use:
echo    %INSTALL_DIR%\deployment\scripts\service_manager.bat
echo    or
echo    %INSTALL_DIR%\deployment\scripts\service_manager.ps1
echo.

endlocal
pause
