@echo off
REM ###############################################################################
REM MBSE Knowledge Graph - Cleanup Script (Windows)
REM Purpose: Remove temporary files, caches, and build artifacts
REM Usage: cleanup.bat
REM ###############################################################################

setlocal enabledelayedexpansion

echo ==========================================
echo MBSE Knowledge Graph - Cleanup Script
echo ==========================================
echo.

REM Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."

cd /d "%PROJECT_ROOT%"

echo Project root: %CD%
echo.

echo === Removing Python cache files ===
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul
del /s /q *.pyd 2>nul
echo [SUCCESS] Python cache cleaned
echo.

echo === Removing test and coverage artifacts ===
if exist ".pytest_cache" rd /s /q ".pytest_cache" && echo [SUCCESS] Removed pytest cache || echo [OK] Already clean: pytest cache
if exist ".coverage" del /q ".coverage" && echo [SUCCESS] Removed coverage data || echo [OK] Already clean: coverage data
if exist "htmlcov" rd /s /q "htmlcov" && echo [SUCCESS] Removed HTML coverage report || echo [OK] Already clean: HTML coverage
if exist ".tox" rd /s /q ".tox" && echo [SUCCESS] Removed tox environments || echo [OK] Already clean: tox
echo.

echo === Removing build artifacts ===
if exist "build" rd /s /q "build" && echo [SUCCESS] Removed build directory || echo [OK] Already clean: build
if exist "dist" rd /s /q "dist" && echo [SUCCESS] Removed dist directory || echo [OK] Already clean: dist
for /d %%d in (*.egg-info) do @if exist "%%d" rd /s /q "%%d" && echo [SUCCESS] Removed %%d
if exist ".eggs" rd /s /q ".eggs" && echo [SUCCESS] Removed eggs directory || echo [OK] Already clean: eggs
echo.

echo === Removing Node.js artifacts ===
if exist "node_modules\.cache" rd /s /q "node_modules\.cache" && echo [SUCCESS] Removed Vite cache || echo [OK] Already clean: Vite cache
if exist ".vite" rd /s /q ".vite" && echo [SUCCESS] Removed Vite temp files || echo [OK] Already clean: Vite temp
if exist "frontend\.vite" rd /s /q "frontend\.vite" && echo [SUCCESS] Removed frontend Vite temp || echo [OK] Already clean: frontend Vite
echo.

echo === Removing log files ===
del /q logs\*.log 2>nul && echo [SUCCESS] Removed application logs || echo [OK] No logs to remove
del /q %TEMP%\backend.log 2>nul
del /q %TEMP%\frontend.log 2>nul
del /q %TEMP%\build.log 2>nul
echo [SUCCESS] Temp logs cleaned
echo.

echo === Removing old backup files ===
del /s /q *.old 2>nul
del /s /q *.bak 2>nul
echo [SUCCESS] Backup files removed
echo.

echo === Removing OS-specific files ===
del /s /q Thumbs.db 2>nul
del /s /q desktop.ini 2>nul
echo [SUCCESS] Windows files removed
echo.

echo === Removing editor temporary files ===
del /s /q *.swp 2>nul
del /s /q *.swo 2>nul
del /s /q *~ 2>nul
echo [SUCCESS] Editor temp files removed
echo.

echo === Optional: Remove node_modules ===
set /p REPLY="Do you want to remove node_modules? (y/N): "
if /i "%REPLY%"=="y" (
    if exist "node_modules" (
        echo Removing node_modules...
        rd /s /q "node_modules"
        echo [SUCCESS] Removed node_modules
        echo [WARNING] Note: Run 'npm install' to reinstall dependencies
    ) else (
        echo [OK] node_modules not found
    )
)
echo.

echo === Cleanup Summary ===
echo [SUCCESS] Cleanup completed successfully!
echo.
echo Cleaned directories:
echo   - Python cache (__pycache__, *.pyc)
echo   - Test artifacts (.pytest_cache, .coverage)
echo   - Build artifacts (dist/, build/)
echo   - Log files (logs/*.log)
echo   - Temporary files (*.old, *.bak)
echo   - OS files (Thumbs.db, desktop.ini)
echo.
echo Ready for deployment!

endlocal
pause
