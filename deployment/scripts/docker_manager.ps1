###############################################################################
# MBSE Knowledge Graph - Docker/Database Management Script (Windows PowerShell)
# Purpose: Manage Neo4j database and Docker containers
# Usage: .\docker_manager.ps1 [start|stop|restart|status|logs|reset]
###############################################################################

param(
    [Parameter(Position=0)]
    [ValidateSet('start', 'stop', 'restart', 'status', 'logs', 'reset', 'neo4j', 'app', 'shell', 'cypher', 'backup', 'help')]
    [string]$Command = 'help',
    
    [Parameter(Position=1)]
    [string]$SubCommand
)

function Show-Usage {
    Write-Host "Usage: .\docker_manager.ps1 [COMMAND]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  start       Start Neo4j database and application containers"
    Write-Host "  stop        Stop all containers"
    Write-Host "  restart     Restart all containers"
    Write-Host "  status      Show container status"
    Write-Host "  logs        View container logs"
    Write-Host "  reset       Stop containers and remove volumes (DESTRUCTIVE)"
    Write-Host "  neo4j       Manage Neo4j only (use with start/stop/restart)"
    Write-Host "  app         Manage application only (use with start/stop/restart)"
    Write-Host "  shell       Open bash shell in application container"
    Write-Host "  cypher      Open Cypher shell for Neo4j"
    Write-Host "  backup      Backup Neo4j database"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\docker_manager.ps1 start          # Start all containers"
    Write-Host "  .\docker_manager.ps1 neo4j start    # Start Neo4j only"
    Write-Host "  .\docker_manager.ps1 logs           # View logs"
    Write-Host "  .\docker_manager.ps1 status         # Check status"
}

# Check if Docker is installed
try {
    docker --version | Out-Null
} catch {
    Write-Host "[ERROR] Docker is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

function Start-Containers {
    Write-Host "Starting MBSE Knowledge Graph with Docker Compose..." -ForegroundColor Blue
    docker-compose up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Containers started" -ForegroundColor Green
        Write-Host ""
        Write-Host "Waiting for Neo4j to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        Show-Status
        Write-Host ""
        Write-Host "Access points:" -ForegroundColor Cyan
        Write-Host "  Neo4j Browser: http://localhost:7474"
        Write-Host "  Bolt Protocol: bolt://localhost:7687"
        Write-Host "  Backend API: http://localhost:5000"
    } else {
        Write-Host "[ERROR] Failed to start containers" -ForegroundColor Red
    }
}

function Stop-Containers {
    Write-Host "Stopping MBSE Knowledge Graph containers..." -ForegroundColor Blue
    docker-compose down
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Containers stopped" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Failed to stop containers" -ForegroundColor Red
    }
}

function Restart-Containers {
    Write-Host "Restarting MBSE Knowledge Graph containers..." -ForegroundColor Blue
    docker-compose restart
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Containers restarted" -ForegroundColor Green
        Show-Status
    } else {
        Write-Host "[ERROR] Failed to restart containers" -ForegroundColor Red
    }
}

function Show-Status {
    Write-Host "=== Container Status ===" -ForegroundColor Cyan
    Write-Host ""
    docker-compose ps
    Write-Host ""
    Write-Host "=== Docker Stats ===" -ForegroundColor Cyan
    docker stats --no-stream --format "table {{.Container}}`t{{.CPUPerc}}`t{{.MemUsage}}`t{{.NetIO}}"
}

function Show-Logs {
    if ($SubCommand -eq "neo4j") {
        Write-Host "Following Neo4j logs... Press Ctrl+C to stop" -ForegroundColor Yellow
        docker-compose logs -f neo4j
    } elseif ($SubCommand -eq "app") {
        Write-Host "Following application logs... Press Ctrl+C to stop" -ForegroundColor Yellow
        docker-compose logs -f app
    } else {
        Write-Host "Following all logs... Press Ctrl+C to stop" -ForegroundColor Yellow
        docker-compose logs -f
    }
}

function Reset-Database {
    Write-Host "[WARNING] This will DESTROY all data in Neo4j database!" -ForegroundColor Red
    $response = Read-Host "Are you sure? Type 'yes' to confirm"
    
    if ($response -ne "yes") {
        Write-Host "Reset cancelled." -ForegroundColor Yellow
        return
    }
    
    Write-Host ""
    Write-Host "Stopping containers and removing volumes..." -ForegroundColor Yellow
    docker-compose down -v
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Containers stopped and volumes removed" -ForegroundColor Green
        Write-Host "Database has been reset. Run '.\docker_manager.ps1 start' to start fresh." -ForegroundColor Cyan
    } else {
        Write-Host "[ERROR] Failed to reset containers" -ForegroundColor Red
    }
}

function Manage-Neo4j {
    switch ($SubCommand) {
        'start' {
            Write-Host "Starting Neo4j container..." -ForegroundColor Blue
            docker-compose up -d neo4j
            Write-Host "[SUCCESS] Neo4j started" -ForegroundColor Green
        }
        'stop' {
            Write-Host "Stopping Neo4j container..." -ForegroundColor Blue
            docker-compose stop neo4j
            Write-Host "[SUCCESS] Neo4j stopped" -ForegroundColor Green
        }
        'restart' {
            Write-Host "Restarting Neo4j container..." -ForegroundColor Blue
            docker-compose restart neo4j
            Write-Host "[SUCCESS] Neo4j restarted" -ForegroundColor Green
        }
        default {
            Write-Host "Usage: .\docker_manager.ps1 neo4j [start|stop|restart]" -ForegroundColor Yellow
        }
    }
}

function Manage-App {
    switch ($SubCommand) {
        'start' {
            Write-Host "Starting application container..." -ForegroundColor Blue
            docker-compose up -d app
            Write-Host "[SUCCESS] Application started" -ForegroundColor Green
        }
        'stop' {
            Write-Host "Stopping application container..." -ForegroundColor Blue
            docker-compose stop app
            Write-Host "[SUCCESS] Application stopped" -ForegroundColor Green
        }
        'restart' {
            Write-Host "Restarting application container..." -ForegroundColor Blue
            docker-compose restart app
            Write-Host "[SUCCESS] Application restarted" -ForegroundColor Green
        }
        default {
            Write-Host "Usage: .\docker_manager.ps1 app [start|stop|restart]" -ForegroundColor Yellow
        }
    }
}

function Open-Shell {
    Write-Host "Opening shell in application container..." -ForegroundColor Blue
    docker-compose exec app bash
}

function Open-CypherShell {
    Write-Host "Opening Cypher shell for Neo4j..." -ForegroundColor Blue
    Write-Host "Use Ctrl+D to exit" -ForegroundColor Yellow
    docker-compose exec neo4j cypher-shell -u neo4j -p password123
}

function Backup-Database {
    Write-Host "Creating Neo4j database backup..." -ForegroundColor Blue
    
    $backupDir = "backups"
    if (-not (Test-Path $backupDir)) {
        New-Item -ItemType Directory -Path $backupDir | Out-Null
    }
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupFile = "$backupDir\neo4j_backup_$timestamp.dump"
    
    Write-Host "Backing up to: $backupFile" -ForegroundColor Cyan
    docker-compose exec -T neo4j neo4j-admin database dump neo4j --to-stdout | Set-Content -Path $backupFile -Encoding Byte
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Backup created: $backupFile" -ForegroundColor Green
        Write-Host ""
        Write-Host "To restore: Get-Content $backupFile -Encoding Byte | docker-compose exec -T neo4j neo4j-admin database load neo4j --from-stdin" -ForegroundColor Cyan
    } else {
        Write-Host "[ERROR] Backup failed" -ForegroundColor Red
    }
}

# Main script logic
switch ($Command) {
    'start' { Start-Containers }
    'stop' { Stop-Containers }
    'restart' { Restart-Containers }
    'status' { Show-Status }
    'logs' { Show-Logs }
    'reset' { Reset-Database }
    'neo4j' { Manage-Neo4j }
    'app' { Manage-App }
    'shell' { Open-Shell }
    'cypher' { Open-CypherShell }
    'backup' { Backup-Database }
    'help' { Show-Usage }
}
