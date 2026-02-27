"""
Dataloader — Schema migration router.

Runs versioned schema migrations tracked via :SchemaMigration nodes.
Also supports running raw Cypher migration files.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from src.dataloader.dependencies import get_neo4j_connection, BACKEND_ROOT, MIGRATIONS_DIR
from src.dataloader.job_manager import job_manager, JobStatus

router = APIRouter(prefix="/migrations", tags=["Schema Migrations"])


class MigrationRunRequest(BaseModel):
    target: Optional[str] = Field(None, description="Migrate up to this migration name (all if not set)")


class CypherMigrationRequest(BaseModel):
    file_path: str = Field(..., description="Path to .cypher file to execute")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _discover_migrations() -> list[dict]:
    """Find numbered migration files in the migrations directory."""
    if not MIGRATIONS_DIR.exists():
        return []

    migrations = []
    for f in sorted(MIGRATIONS_DIR.glob("*.py")):
        if f.name.startswith("__"):
            continue
        # Extract number prefix if present
        parts = f.stem.split("_", 1)
        try:
            num = int(parts[0])
        except ValueError:
            continue
        migrations.append({
            "number": num,
            "name": f.stem,
            "file": str(f),
        })
    return sorted(migrations, key=lambda m: m["number"])


def _get_applied_migrations(conn) -> set[str]:
    """Query Neo4j for already-applied migration names."""
    try:
        result = conn.execute_query(
            "MATCH (m:SchemaMigration) RETURN m.name AS name"
        )
        return {r["name"] for r in result}
    except Exception:
        return set()


def _run_migration_file(conn, filepath: str, name: str) -> dict:
    """Import and execute a single migration file's up() function."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if hasattr(mod, "up"):
        mod.up(conn)
    else:
        raise ValueError(f"Migration {name} has no up() function")

    # Record as applied
    conn.execute_query(
        "CREATE (m:SchemaMigration {name: $name, applied_at: datetime()}) RETURN m",
        {"name": name},
    )
    return {"name": name, "status": "applied"}


def _run_migrations_job(job_id: str, target: Optional[str]):
    """Background migration runner."""
    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message="Discovering migrations...")

        migrations = _discover_migrations()
        conn = get_neo4j_connection()
        try:
            applied = _get_applied_migrations(conn)
            pending = [m for m in migrations if m["name"] not in applied]

            if target:
                pending = [m for m in pending if m["name"] <= target]

            if not pending:
                job_manager.update(
                    job_id, status=JobStatus.COMPLETED, progress=100,
                    message="No pending migrations",
                    result={"applied": len(applied), "pending": 0},
                )
                return

            results = []
            for i, m in enumerate(pending, 1):
                pct = int(i / len(pending) * 100)
                job_manager.update(job_id, progress=pct, message=f"Running {m['name']}...")
                try:
                    res = _run_migration_file(conn, m["file"], m["name"])
                    results.append(res)
                except Exception as e:
                    results.append({"name": m["name"], "status": "failed", "error": str(e)})
                    break  # Stop on first failure

            job_manager.update(
                job_id, status=JobStatus.COMPLETED, progress=100,
                message=f"Applied {len(results)} migration(s)",
                result={"results": results},
            )
        finally:
            conn.close()
    except Exception as e:
        logger.exception(f"Migration job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


def _run_cypher_job(job_id: str, file_path: str):
    """Background raw Cypher file execution."""
    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message=f"Executing {file_path}...")

        p = Path(file_path)
        cypher_text = p.read_text(encoding="utf-8")

        # Split on semicolons for multi-statement files
        statements = [s.strip() for s in cypher_text.split(";") if s.strip()]

        conn = get_neo4j_connection()
        try:
            executed = 0
            for i, stmt in enumerate(statements, 1):
                if stmt.upper().startswith("//") or not stmt:
                    continue
                pct = int(i / len(statements) * 100)
                job_manager.update(job_id, progress=pct, message=f"Statement {i}/{len(statements)}")
                conn.execute_query(stmt)
                executed += 1

            job_manager.update(
                job_id, status=JobStatus.COMPLETED, progress=100,
                message=f"Executed {executed} Cypher statements",
                result={"file": file_path, "statements_executed": executed},
            )
        finally:
            conn.close()
    except Exception as e:
        logger.exception(f"Cypher job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/run", summary="Apply pending schema migrations")
async def run_migrations(req: MigrationRunRequest, background_tasks: BackgroundTasks):
    """Apply all pending numbered migrations from backend/scripts/migrations/."""
    job = job_manager.create("schema_migration", req.model_dump())
    background_tasks.add_task(_run_migrations_job, job.job_id, req.target)
    return {"job_id": job.job_id}


@router.post("/cypher", summary="Execute raw Cypher migration file")
async def run_cypher_file(req: CypherMigrationRequest, background_tasks: BackgroundTasks):
    """Execute a .cypher file directly against Neo4j."""
    p = Path(req.file_path)
    if not p.exists():
        raise HTTPException(404, f"File not found: {req.file_path}")
    if not p.suffix.lower() == ".cypher":
        raise HTTPException(400, "File must be .cypher")

    job = job_manager.create("cypher_execution", {"file_path": req.file_path})
    background_tasks.add_task(_run_cypher_job, job.job_id, req.file_path)
    return {"job_id": job.job_id, "file": req.file_path}


@router.get("/status", summary="Show migration status")
async def migration_status():
    """List all migrations and their applied status."""
    migrations = _discover_migrations()
    conn = get_neo4j_connection()
    try:
        applied = _get_applied_migrations(conn)
        for m in migrations:
            m["applied"] = m["name"] in applied
        return {
            "total": len(migrations),
            "applied": len(applied),
            "pending": len([m for m in migrations if not m["applied"]]),
            "migrations": migrations,
        }
    finally:
        conn.close()


@router.get("/cypher-files", summary="List available .cypher files")
async def list_cypher_files():
    """List .cypher files in the migrations directory."""
    found = []
    if MIGRATIONS_DIR.exists():
        for f in sorted(MIGRATIONS_DIR.glob("*.cypher")):
            found.append({"name": f.name, "path": str(f), "size": f.stat().st_size})
    return {"directory": str(MIGRATIONS_DIR), "files": found}
