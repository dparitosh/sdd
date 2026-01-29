"""Pytest configuration.

Loads environment variables from `.env` when present so tests and local runs
share a single source of configuration.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from loguru import logger


def _is_truthy_env(name: str) -> bool:
    val = os.getenv(name, "").strip().lower()
    return val in {"1", "true", "yes", "y", "on"}


_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[3]

# Ensure both `import src...` and `import web...` work in tests.
for _p in (str(_BACKEND_DIR), str(_BACKEND_DIR / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def pytest_configure():
    env_file = _REPO_ROOT / ".env"

    if env_file.exists():
        # Do not override variables already provided by the environment/CI.
        load_dotenv(env_file, override=False)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Make integration tests opt-in.

    The repository supports running against an external Neo4j instance. Since
    local Neo4j may not be available (e.g., when Docker support is removed), we
    treat tests under `tests/integration/` as opt-in.

    Enable them with:
      PYTEST_RUN_INTEGRATION=1

    When integration tests are disabled, the session-scoped `api_server` fixture
    becomes a no-op so unit tests can run without Neo4j.
    """

    run_integration = _is_truthy_env("PYTEST_RUN_INTEGRATION")
    has_integration = False

    for item in items:
        path = str(getattr(item, "fspath", "")).replace("\\", "/").lower()
        if "/tests/integration/" in path:
            has_integration = True
            if not run_integration:
                item.add_marker(
                    pytest.mark.skip(
                        reason=(
                            "Integration tests are disabled by default. "
                            "Set PYTEST_RUN_INTEGRATION=1 and configure Neo4j (NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD) to enable."
                        )
                    )
                )

    # Used by the session autouse fixture to avoid starting services when
    # integration tests are not running.
    setattr(config, "_mbse_run_integration", bool(has_integration and run_integration))


def _wait_for_http_ok(url: str, timeout_seconds: int = 60) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def _seed_neo4j_if_empty() -> None:
    """Seed a minimal graph into Neo4j when the database is empty.

    CI starts with a fresh Neo4j container, but the integration suite expects at
    least one Class/Property and some relationships.
    """
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    if not neo4j_uri:
        # Let the app's startup error message handle missing configuration.
        logger.warning("NEO4J_URI not set; skipping test seeding")
        return

    from src.graph.connection import Neo4jConnection

    try:
        with Neo4jConnection(neo4j_uri, neo4j_user, neo4j_password) as conn:
            result = conn.execute_query("MATCH (n) RETURN count(n) as count")
            node_count = int(result[0]["count"]) if result else 0
            if node_count > 0:
                return
    except Exception as exc:
        raise RuntimeError(
            "Unable to connect to Neo4j for integration test seeding. "
            "Ensure Neo4j is running and configured via NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD."
        ) from exc

        logger.info("Seeding Neo4j with minimal test data (empty database)")

        # Minimal nodes required by integration tests.
        conn.execute_write(
            """
                        MERGE (c1:Class {id: $id1})
                        ON CREATE SET c1.name = $name1
                        MERGE (c2:Class {id: $id2})
                        ON CREATE SET c2.name = $name2
                        MERGE (p1:Property {id: $prop_id})
                        ON CREATE SET
                            p1.name = $prop_name,
                            p1.visibility = 'public',
                            p1.lower = 1,
                            p1.upper = 1,
                            p1.defaultValue = '0',
                            p1.isDerived = false,
                            p1.isReadOnly = false
                        MERGE (dt:DataType {id: $dt_id})
                        ON CREATE SET dt.name = $dt_name, dt.type = 'uml:DataType'
                        MERGE (req:Requirement {id: $req_id})
                        ON CREATE SET
                            req.name = $req_name,
                            req.type = 'uml:Requirement',
                            req.text = $req_text,
                            req.priority = 'High',
                            req.status = 'Approved'
                        MERGE (con:Constraint {id: $con_id})
                        ON CREATE SET
                            con.name = $con_name,
                            con.body = $con_body,
                            con.language = 'OCL',
                            con.type = 'invariant'
                        WITH c1, c2, p1, dt, req, con
                        MERGE (c1)-[:HAS_ATTRIBUTE]->(p1)
                        MERGE (p1)-[:TYPED_BY]->(dt)
                        MERGE (p1)-[:HAS_RULE]->(con)
                        MERGE (req)-[:SHOULD_BE_SATISFIED_BY]->(c1)
                        MERGE (c1)-[:CONTAINS]->(c2)
                        """,
            {
                "id1": "_CLASS_001",
                "name1": "System",
                "id2": "_CLASS_002",
                "name2": "Subsystem",
                "prop_id": "_PROP_001",
                "prop_name": "mass",
                "dt_id": "_DT_KILOGRAM",
                "dt_name": "Kilogram",
                "req_id": "_REQ_PERF_002",
                "req_name": "Response Time",
                "req_text": "System shall respond to user inputs within 100ms",
                "con_id": "_CONSTRAINT_001",
                "con_name": "Validate_mass",
                "con_body": "self.mass > 0",
            },
        )


@pytest.fixture(scope="session", autouse=True)
def api_server(pytestconfig: pytest.Config):
    """Start FastAPI (uvicorn) for integration tests.

    The integration suite uses real HTTP calls to http://127.0.0.1:5000.
    This fixture ensures a server is running during the test session.
    """
    # If integration tests are not enabled/collected, don't pay the startup cost.
    if os.getenv("PYTEST_NO_API_SERVER") or not getattr(
        pytestconfig, "_mbse_run_integration", False
    ):
        yield
        return

    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:5000")
    health_url = f"{base_url}/api/health"

    # If a server is already running (e.g., local dev), reuse it.
    if _wait_for_http_ok(health_url, timeout_seconds=2):
        yield
        return

    # Ensure the graph has at least minimal test data (CI starts empty).
    _seed_neo4j_if_empty()

    # Start uvicorn using the same interpreter pytest is running under.
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.web.app_fastapi:app",
        "--host",
        "127.0.0.1",
        "--port",
        "5000",
        "--log-level",
        "warning",
    ]

    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    logs_dir = _REPO_ROOT / "backend" / "tests" / ".logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "uvicorn-test-server.log"

    with open(log_path, "w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=log_file,
            cwd=str(_BACKEND_DIR),
            env=os.environ.copy(),
            creationflags=creationflags,
        )

    try:
        if not _wait_for_http_ok(health_url, timeout_seconds=90):
            tail = ""
            try:
                if log_path.exists():
                    tail = "\n".join(
                        log_path.read_text(encoding="utf-8").splitlines()[-80:]
                    )
            except Exception:
                tail = ""

            raise RuntimeError(
                "FastAPI test server did not become ready at "
                f"{health_url}. Check Neo4j configuration in .env (NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD) "
                "and ensure port 5000 is available. "
                f"Uvicorn log: {log_path}\n\n{tail}".rstrip()
            )
        yield
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
