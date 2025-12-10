@echo off
REM ###############################################################################
REM MBSE Knowledge Graph - Service Management Script (Windows)
REM Purpose: Start, stop, restart, and monitor services
REM Usage: service_manager.bat [start|stop|restart|status|logs]
REM ###############################################################################

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
set "PID_DIR=%TEMP%\mbse-pids"

if not exist "%PID_DIR%" mkdir "%PID_DIR%"

if "%1"=="" goto :usage
if "%1"=="help" goto :usage
if "%1"=="-h" goto :usage
if "%1"=="/?" goto :usage

goto :%1 2>nul || goto :usage

:usage
echo Usage: %~nx0 [COMMAND]
echo.
echo Commands:
echo   start      Start backend and frontend services
echo   stop       Stop all services
echo   restart    Restart all services
echo   status     Show service status
echo   logs       View service logs
echo   backend    Manage backend only (use with start/stop/restart)
echo   frontend   Manage frontend only (use with start/stop/restart)
echo.
echo Examples:
echo   %~nx0 start          # Start all services
echo   %~nx0 backend start  # Start backend only
echo   %~nx0 status         # Check status
goto :eof

:start
echo Starting MBSE Knowledge Graph services...
call :start_backend
timeout /t 2 /nobreak >nul
call :start_frontend
echo.
echo [SUCCESS] Services started. Check status with: %~nx0 status
goto :eof

:stop
echo Stopping MBSE Knowledge Graph services...
call :stop_frontend
call :stop_backend
echo.
echo [SUCCESS] Services stopped
goto :eof

:restart
echo Restarting MBSE Knowledge Graph services...
call :stop_frontend
call :stop_backend
timeout /t 2 /nobreak >nul
call :start_backend
timeout /t 2 /nobreak >nul
call :start_frontend
echo.
echo [SUCCESS] Services restarted
goto :eof

:status
echo === Service Status ===
echo.
echo Backend Service:
if exist "%PID_DIR%\backend.pid" (
    set /p BACKEND_PID=<"%PID_DIR%\backend.pid"
    tasklist /FI "PID eq !BACKEND_PID!" 2>nul | find "!BACKEND_PID!" >nul
    if !errorlevel! equ 0 (
        echo [RUNNING] Backend running with PID: !BACKEND_PID!
    ) else (
        echo [STOPPED] Backend not running
        del "%PID_DIR%\backend.pid" 2>nul
    )
) else (
    echo [STOPPED] Backend not running
)
echo.
echo Frontend Service:
if exist "%PID_DIR%\frontend.pid" (
    set /p FRONTEND_PID=<"%PID_DIR%\frontend.pid"
    tasklist /FI "PID eq !FRONTEND_PID!" 2>nul | find "!FRONTEND_PID!" >nul
    if !errorlevel! equ 0 (
        echo [RUNNING] Frontend running with PID: !FRONTEND_PID!
    ) else (
        echo [STOPPED] Frontend not running
        del "%PID_DIR%\frontend.pid" 2>nul
    )
) else (
    echo [STOPPED] Frontend not running
)
echo.
echo Process details:
tasklist | findstr /i "python node"
goto :eof

:logs
echo === Service Logs ===
echo.
if exist "%TEMP%\mbse-backend.log" (
    echo --- Backend Log (last 20 lines) ---
    powershell -Command "Get-Content '%TEMP%\mbse-backend.log' -Tail 20"
    echo.
)
if exist "%TEMP%\mbse-frontend.log" (
    echo --- Frontend Log (last 20 lines) ---
    powershell -Command "Get-Content '%TEMP%\mbse-frontend.log' -Tail 20"
    echo.
)
if not exist "%TEMP%\mbse-backend.log" if not exist "%TEMP%\mbse-frontend.log" (
    echo No log files found
)
goto :eof

:backend
if "%2"=="start" call :start_backend
if "%2"=="stop" call :stop_backend
if "%2"=="restart" (
    call :stop_backend
    timeout /t 2 /nobreak >nul
    call :start_backend
)
if "%2"=="" echo Usage: %~nx0 backend [start^|stop^|restart]
goto :eof

:frontend
if "%2"=="start" call :start_frontend
if "%2"=="stop" call :stop_frontend
if "%2"=="restart" (
    call :stop_frontend
    timeout /t 2 /nobreak >nul
    call :start_frontend
)
if "%2"=="" echo Usage: %~nx0 frontend [start^|stop^|restart]
goto :eof

REM Internal functions

:start_backend
echo Starting backend...
cd /d "%PROJECT_ROOT%"
set PYTHONPATH=%CD%
start /b cmd /c "python -m src.web.app > %TEMP%\mbse-backend.log 2>&1"
timeout /t 2 /nobreak >nul
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /NH ^| findstr /i "python"') do (
    echo %%a > "%PID_DIR%\backend.pid"
    echo [SUCCESS] Backend started with PID: %%a
    goto :backend_started
)
echo [ERROR] Failed to start backend
:backend_started
goto :eof

:stop_backend
echo Stopping backend...
if exist "%PID_DIR%\backend.pid" (
    set /p BACKEND_PID=<"%PID_DIR%\backend.pid"
    taskkill /PID !BACKEND_PID! /F >nul 2>&1
    del "%PID_DIR%\backend.pid" 2>nul
    echo [SUCCESS] Backend stopped
) else (
    taskkill /F /IM python.exe /FI "WINDOWTITLE eq *src.web.app*" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [SUCCESS] Backend stopped
    ) else (
        echo [WARNING] Backend not running
    )
)
goto :eof

:start_frontend
echo Starting frontend...
cd /d "%PROJECT_ROOT%"
start /b cmd /c "npm run preview -- --host 0.0.0.0 --port 3001 > %TEMP%\mbse-frontend.log 2>&1"
timeout /t 2 /nobreak >nul
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq node.exe" /NH ^| findstr /i "node"') do (
    echo %%a > "%PID_DIR%\frontend.pid"
    echo [SUCCESS] Frontend started with PID: %%a
    goto :frontend_started
)
echo [ERROR] Failed to start frontend
:frontend_started
goto :eof

:stop_frontend
echo Stopping frontend...
if exist "%PID_DIR%\frontend.pid" (
    set /p FRONTEND_PID=<"%PID_DIR%\frontend.pid"
    taskkill /PID !FRONTEND_PID! /F /T >nul 2>&1
    del "%PID_DIR%\frontend.pid" 2>nul
    echo [SUCCESS] Frontend stopped
) else (
    taskkill /F /IM node.exe >nul 2>&1
    if !errorlevel! equ 0 (
        echo [SUCCESS] Frontend stopped
    ) else (
        echo [WARNING] Frontend not running
    )
)
goto :eof

endlocal
