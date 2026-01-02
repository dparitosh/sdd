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


@pytest.fixture(scope="session", autouse=True)
def api_server():
    """Start FastAPI (uvicorn) for integration tests.

    The integration suite uses real HTTP calls to http://127.0.0.1:5000.
    This fixture ensures a server is running during the test session.
    """
    # If the suite is run without integration tests, don't pay the startup cost.
    # (pytest doesn't give us the collection list here reliably across versions,
    # so we use a simple opt-out switch.)
    if os.getenv("PYTEST_NO_API_SERVER"):
        yield
        return

    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:5000")
    health_url = f"{base_url}/api/health"

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

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(_BACKEND_DIR),
        env=os.environ.copy(),
        creationflags=creationflags,
    )

    try:
        if not _wait_for_http_ok(health_url, timeout_seconds=90):
            raise RuntimeError(
                "FastAPI test server did not become ready at "
                f"{health_url}. Check Neo4j configuration in .env (NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD) "
                "and ensure port 5000 is available."
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
