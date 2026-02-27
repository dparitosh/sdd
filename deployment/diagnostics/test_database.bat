@echo off
REM ###############################################################################
REM MBSE Knowledge Graph - Database Diagnostics (Windows)
REM Purpose: Test Neo4j connectivity and performance
REM Usage: test_database.bat
REM ###############################################################################

setlocal enabledelayedexpansion

echo ==========================================
echo Neo4j Database Diagnostics
echo ==========================================
echo.

REM Load environment variables from .env file
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        set "%%a=%%b"
    )
    echo [SUCCESS] Environment loaded from .env
) else (
    echo [ERROR] .env file not found
    exit /b 1
)

REM Check required variables
if "%NEO4J_URI%"=="" (
    echo [ERROR] NEO4J_URI not set in .env
    exit /b 1
)
if "%NEO4J_USER%"=="" (
    echo [ERROR] NEO4J_USER not set in .env
    exit /b 1
)
if "%NEO4J_PASSWORD%"=="" (
    echo [ERROR] NEO4J_PASSWORD not set in .env
    exit /b 1
)

echo.
echo Configuration:
echo   URI: %NEO4J_URI%
echo   User: %NEO4J_USER%
if "%NEO4J_DATABASE%"=="" (
    set NEO4J_DATABASE=neo4j
)
echo   Database: %NEO4J_DATABASE%
echo.

REM Test 1: Python driver connectivity
echo === Test 1: Python Driver Connectivity ===
python -c "import sys; from neo4j import GraphDatabase; import os; uri = os.getenv('NEO4J_URI'); user = os.getenv('NEO4J_USER'); password = os.getenv('NEO4J_PASSWORD'); driver = GraphDatabase.driver(uri, auth=(user, password)); driver.verify_connectivity(); print('[SUCCESS] Connection successful'); session = driver.session(database=os.getenv('NEO4J_DATABASE', 'neo4j')); result = session.run('RETURN 1 as test'); record = result.single(); print('[SUCCESS] Query execution successful') if record['test'] == 1 else None; session.close(); driver.close()"

if %errorLevel% equ 0 (
    echo [SUCCESS] Python driver test passed
) else (
    echo [ERROR] Python driver test failed
    exit /b 1
)

echo.

REM Test 2: Database statistics
echo === Test 2: Database Statistics ===
python -c "from neo4j import GraphDatabase; import os; uri = os.getenv('NEO4J_URI'); user = os.getenv('NEO4J_USER'); password = os.getenv('NEO4J_PASSWORD'); db = os.getenv('NEO4J_DATABASE', 'neo4j'); driver = GraphDatabase.driver(uri, auth=(user, password)); session = driver.session(database=db); result = session.run('MATCH (n) RETURN count(n) as node_count'); print(f'Nodes: {result.single()[\"node_count\"]}'); result = session.run('MATCH ()-[r]->() RETURN count(r) as rel_count'); print(f'Relationships: {result.single()[\"rel_count\"]}'); result = session.run('CALL db.labels()'); labels = [record['label'] for record in result]; print(f'Labels: {len(labels)}'); [print(f'  - {label}') for label in labels[:10]]; result = session.run('CALL db.relationshipTypes()'); types = [record['relationshipType'] for record in result]; print(f'Relationship Types: {len(types)}'); [print(f'  - {t}') for t in types[:10]]; session.close(); driver.close()"

if %errorLevel% equ 0 (
    echo.
    echo [SUCCESS] Database statistics retrieved
) else (
    echo [ERROR] Failed to retrieve statistics
)

echo.

REM Test 3: Query performance
echo === Test 3: Query Performance ===
python -c "from neo4j import GraphDatabase; import os; import time; uri = os.getenv('NEO4J_URI'); user = os.getenv('NEO4J_USER'); password = os.getenv('NEO4J_PASSWORD'); db = os.getenv('NEO4J_DATABASE', 'neo4j'); driver = GraphDatabase.driver(uri, auth=(user, password)); session = driver.session(database=db); start = time.time(); session.run('RETURN 1').consume(); latency = (time.time() - start) * 1000; print(f'Simple query latency: {latency:.2f}ms'); status = 'GOOD' if latency < 100 else 'SLOW' if latency < 500 else 'CRITICAL'; print(f'Status: {status}'); session.close(); driver.close()"

echo.

REM Test 4: Check if database is populated
echo === Test 4: Database Content Check ===
python -c "from neo4j import GraphDatabase; import os; uri = os.getenv('NEO4J_URI'); user = os.getenv('NEO4J_USER'); password = os.getenv('NEO4J_PASSWORD'); db = os.getenv('NEO4J_DATABASE', 'neo4j'); driver = GraphDatabase.driver(uri, auth=(user, password)); session = driver.session(database=db); result = session.run('MATCH (n) RETURN count(n) as count'); count = result.single()['count']; print(f'Total nodes: {count}'); print('[SUCCESS] Database is populated' if count > 0 else '[WARNING] Database is empty'); session.close(); driver.close()"

echo.
echo ==========================================
echo Diagnostics Complete
echo ==========================================

endlocal
pause
