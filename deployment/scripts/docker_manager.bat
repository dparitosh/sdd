@echo off
REM ###############################################################################
REM MBSE Knowledge Graph - Docker/Database Management Script (Windows)
REM Purpose: Manage Neo4j database and Docker containers
REM Usage: docker_manager.bat [start|stop|restart|status|logs|reset]
REM ###############################################################################

setlocal enabledelayedexpansion

if "%1"=="" goto :usage
if "%1"=="help" goto :usage
if "%1"=="-h" goto :usage
if "%1"=="/?" goto :usage

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
    exit /b 1
)

goto :%1 2>nul || goto :usage

:usage
echo Usage: %~nx0 [COMMAND]
echo.
echo Commands:
echo   start       Start Neo4j database and application containers
echo   stop        Stop all containers
echo   restart     Restart all containers
echo   status      Show container status
echo   logs        View container logs
echo   reset       Stop containers and remove volumes (DESTRUCTIVE)
echo   neo4j       Manage Neo4j only (use with start/stop/restart)
echo   app         Manage application only (use with start/stop/restart)
echo   shell       Open bash shell in application container
echo   cypher      Open Cypher shell for Neo4j
echo   backup      Backup Neo4j database
echo.
echo Examples:
echo   %~nx0 start          # Start all containers
echo   %~nx0 neo4j start    # Start Neo4j only
echo   %~nx0 logs           # View logs
echo   %~nx0 status         # Check status
goto :eof

:start
echo Starting MBSE Knowledge Graph with Docker Compose...
docker-compose up -d
if %errorLevel% equ 0 (
    echo [SUCCESS] Containers started
    echo.
    echo Waiting for Neo4j to be ready...
    timeout /t 10 /nobreak >nul
    call :status
    echo.
    echo Access points:
    echo   Neo4j Browser: http://localhost:7474
    echo   Bolt Protocol: bolt://localhost:7687
    echo   Backend API: http://localhost:5000
) else (
    echo [ERROR] Failed to start containers
)
goto :eof

:stop
echo Stopping MBSE Knowledge Graph containers...
docker-compose down
if %errorLevel% equ 0 (
    echo [SUCCESS] Containers stopped
) else (
    echo [ERROR] Failed to stop containers
)
goto :eof

:restart
echo Restarting MBSE Knowledge Graph containers...
docker-compose restart
if %errorLevel% equ 0 (
    echo [SUCCESS] Containers restarted
    call :status
) else (
    echo [ERROR] Failed to restart containers
)
goto :eof

:status
echo === Container Status ===
echo.
docker-compose ps
echo.
echo === Docker Stats ===
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>nul
goto :eof

:logs
if "%2"=="neo4j" (
    echo Following Neo4j logs... Press Ctrl+C to stop
    docker-compose logs -f neo4j
) else if "%2"=="app" (
    echo Following application logs... Press Ctrl+C to stop
    docker-compose logs -f app
) else (
    echo Following all logs... Press Ctrl+C to stop
    docker-compose logs -f
)
goto :eof

:reset
echo [WARNING] This will DESTROY all data in Neo4j database!
set /p REPLY="Are you sure? Type 'yes' to confirm: "
if /i not "%REPLY%"=="yes" (
    echo Reset cancelled.
    goto :eof
)
echo.
echo Stopping containers and removing volumes...
docker-compose down -v
if %errorLevel% equ 0 (
    echo [SUCCESS] Containers stopped and volumes removed
    echo Database has been reset. Run '%~nx0 start' to start fresh.
) else (
    echo [ERROR] Failed to reset containers
)
goto :eof

:neo4j
if "%2"=="start" (
    echo Starting Neo4j container...
    docker-compose up -d neo4j
    echo [SUCCESS] Neo4j started
)
if "%2"=="stop" (
    echo Stopping Neo4j container...
    docker-compose stop neo4j
    echo [SUCCESS] Neo4j stopped
)
if "%2"=="restart" (
    echo Restarting Neo4j container...
    docker-compose restart neo4j
    echo [SUCCESS] Neo4j restarted
)
if "%2"=="" echo Usage: %~nx0 neo4j [start^|stop^|restart]
goto :eof

:app
if "%2"=="start" (
    echo Starting application container...
    docker-compose up -d app
    echo [SUCCESS] Application started
)
if "%2"=="stop" (
    echo Stopping application container...
    docker-compose stop app
    echo [SUCCESS] Application stopped
)
if "%2"=="restart" (
    echo Restarting application container...
    docker-compose restart app
    echo [SUCCESS] Application restarted
)
if "%2"=="" echo Usage: %~nx0 app [start^|stop^|restart]
goto :eof

:shell
echo Opening shell in application container...
docker-compose exec app bash
goto :eof

:cypher
echo Opening Cypher shell for Neo4j...
echo Use Ctrl+D to exit
docker-compose exec neo4j cypher-shell -u neo4j -p password123
goto :eof

:backup
echo Creating Neo4j database backup...
set BACKUP_DIR=backups
set TIMESTAMP=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set BACKUP_FILE=%BACKUP_DIR%\neo4j_backup_%TIMESTAMP%.dump

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo Backing up to: %BACKUP_FILE%
docker-compose exec -T neo4j neo4j-admin database dump neo4j --to-stdout > "%BACKUP_FILE%"

if %errorLevel% equ 0 (
    echo [SUCCESS] Backup created: %BACKUP_FILE%
    echo.
    echo To restore: docker-compose exec -T neo4j neo4j-admin database load neo4j --from-stdin ^< %BACKUP_FILE%
) else (
    echo [ERROR] Backup failed
)
goto :eof

endlocal
