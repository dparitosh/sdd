@echo off
REM ###############################################################################
REM MBSE Knowledge Graph - Service Management Script (Windows)
REM Purpose: Start, stop, restart, and monitor services
REM Usage: service_manager.bat [start|stop|restart|status|logs]
REM ###############################################################################

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
set "FRONTEND_DIR=%PROJECT_ROOT%\frontend"
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
echo.
echo Manual mode env vars (must be set in .env):
echo   BACKEND_HOST
echo   BACKEND_PORT
echo   FRONTEND_HOST
echo   FRONTEND_PORT
echo   API_BASE_URL
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

call :load_env

set "PYTHON_EXE=python"
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"

if "%NEO4J_URI%"=="" (echo [ERROR] Missing NEO4J_URI in .env & goto :eof)
if "%NEO4J_USER%"=="" (echo [ERROR] Missing NEO4J_USER in .env & goto :eof)
if "%NEO4J_PASSWORD%"=="" (echo [ERROR] Missing NEO4J_PASSWORD in .env & goto :eof)
if "%BACKEND_HOST%"=="" (echo [ERROR] Missing BACKEND_HOST in .env & goto :eof)
if "%BACKEND_PORT%"=="" (echo [ERROR] Missing BACKEND_PORT in .env & goto :eof)

for /f %%a in ('powershell -NoProfile -Command "$pythonExe='%PYTHON_EXE%'; $p=Start-Process -FilePath $pythonExe -ArgumentList @('-m','uvicorn','src.web.app_fastapi:app','--host','%BACKEND_HOST%','--port','%BACKEND_PORT%') -RedirectStandardOutput '%TEMP%\mbse-backend.log' -RedirectStandardError '%TEMP%\mbse-backend-error.log' -PassThru -WindowStyle Hidden; $p.Id"') do (
    echo %%a > "%PID_DIR%\backend.pid"
)
if exist "%PID_DIR%\backend.pid" (
    set /p BACKEND_PID=<"%PID_DIR%\backend.pid"
    echo [SUCCESS] Backend started with PID: %BACKEND_PID%
) else (
    echo [ERROR] Failed to start backend
)
goto :eof

:stop_backend
echo Stopping backend...
if exist "%PID_DIR%\backend.pid" (
    set /p BACKEND_PID=<"%PID_DIR%\backend.pid"
    taskkill /PID !BACKEND_PID! /F >nul 2>&1
    del "%PID_DIR%\backend.pid" 2>nul
    echo [SUCCESS] Backend stopped
) else (
    echo [WARNING] Backend PID file not found; not stopping arbitrary python.exe
)
goto :eof

:start_frontend
echo Starting frontend...
cd /d "%PROJECT_ROOT%"

call :load_env

if "%FRONTEND_HOST%"=="" (echo [ERROR] Missing FRONTEND_HOST in .env & goto :eof)
if "%FRONTEND_PORT%"=="" (echo [ERROR] Missing FRONTEND_PORT in .env & goto :eof)
if "%API_BASE_URL%"=="" (echo [ERROR] Missing API_BASE_URL in .env & goto :eof)

for /f %%a in ('powershell -NoProfile -Command "$npmCmd = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source; if (-not $npmCmd) { $npmCmd = (Get-Command npm -ErrorAction Stop).Source }; $p=Start-Process -FilePath $npmCmd -ArgumentList @('run','dev','--','--host','%FRONTEND_HOST%','--port','%FRONTEND_PORT%') -RedirectStandardOutput '%TEMP%\mbse-frontend.log' -RedirectStandardError '%TEMP%\mbse-frontend-error.log' -PassThru -WindowStyle Hidden; $p.Id"') do (
    echo %%a > "%PID_DIR%\frontend.pid"
)
if exist "%PID_DIR%\frontend.pid" (
    set /p FRONTEND_PID=<"%PID_DIR%\frontend.pid"
    echo [SUCCESS] Frontend started with PID: %FRONTEND_PID%
) else (
    echo [ERROR] Failed to start frontend
)
goto :eof

:stop_frontend
echo Stopping frontend...
if exist "%PID_DIR%\frontend.pid" (
    set /p FRONTEND_PID=<"%PID_DIR%\frontend.pid"
    taskkill /PID !FRONTEND_PID! /F /T >nul 2>&1
    del "%PID_DIR%\frontend.pid" 2>nul
    echo [SUCCESS] Frontend stopped
) else (
    echo [WARNING] Frontend PID file not found; not stopping arbitrary node.exe
)
goto :eof

endlocal

goto :eof

:load_env
REM Load variables from .env at project root (does not override existing vars)
if not exist "%PROJECT_ROOT%\.env" goto :eof
for /f "usebackq eol=# tokens=1* delims==" %%A in ("%PROJECT_ROOT%\.env") do (
    if "%%A"=="" (
        REM skip
    ) else (
        if "!%%A!"=="" set "%%A=%%B"
    )
)
goto :eof
