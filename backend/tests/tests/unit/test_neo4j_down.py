"""
Unit tests for Neo4j-down / degraded-mode behaviour.

When Neo4j is unreachable at startup the application must:
1. NOT crash — uvicorn should start and accept HTTP connections.
2. /api/health returns 503 with structured JSON indicating "unhealthy".
3. /info returns 200 (no Neo4j required).
4. Database-dependent routes (e.g. /api/graph/data) return 503.
5. /api/docs Swagger UI returns 200.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_singletons():
    """
    Reset all module-level singletons before/after each test so tests are
    isolated and don't bleed state.
    """
    import src.web.services.neo4j_service as ns
    import src.web.container as ct

    # Save originals
    orig_service = ns._neo4j_service
    orig_degraded = ns._degraded_mode
    orig_container = ct.ServiceContainer._instance

    yield

    # Restore
    ns._neo4j_service = orig_service
    ns._degraded_mode = orig_degraded
    ct.ServiceContainer._instance = orig_container


@pytest.fixture()
def degraded_client():
    """
    Return a TestClient whose app was started with Neo4j **unreachable**.

    We patch ``Neo4jService.__init__`` to raise immediately (simulating
    a dead Neo4j server) and rely on the lifespan + container logic to
    enter degraded mode.
    """
    from neo4j.exceptions import ServiceUnavailable

    # Reset container so lifespan creates a fresh one
    from src.web.container import ServiceContainer
    ServiceContainer.reset()

    # Reset legacy module-level singleton
    import src.web.services.neo4j_service as ns
    ns._neo4j_service = None
    ns._degraded_mode = False

    def _fake_init(self, *args, **kwargs):
        """Raise ServiceUnavailable to simulate unreachable Neo4j."""
        raise ServiceUnavailable("Simulated: Neo4j is unreachable")

    with patch.object(
        ns.Neo4jService, "__init__", _fake_init
    ):
        from src.web.app_fastapi import app
        client = TestClient(app, raise_server_exceptions=False)
        yield client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDegradedMode:
    """Verify the app works in degraded mode (Neo4j down)."""

    def test_health_returns_503(self, degraded_client):
        """GET /api/health must return 503 with structured JSON."""
        resp = degraded_client.get("/api/health")
        assert resp.status_code == 503, f"Expected 503 got {resp.status_code}"

        body = resp.json()
        assert body["status"] == "unhealthy"
        assert body["database"]["connected"] is False
        assert body["database"]["error"] is not None
        assert "degraded" in body["database"]["error"].lower() or "unavailable" in body["database"]["error"].lower()

    def test_info_returns_200(self, degraded_client):
        """GET /info should work even when Neo4j is down."""
        resp = degraded_client.get("/info")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "MBSE Knowledge Graph REST API"

    def test_docs_returns_200(self, degraded_client):
        """Swagger UI must still be served."""
        resp = degraded_client.get("/api/docs")
        assert resp.status_code == 200

    def test_graph_data_returns_503(self, degraded_client):
        """A database-dependent route should return 503, not 500."""
        resp = degraded_client.get("/api/graph/data")
        assert resp.status_code == 503, f"Expected 503 but got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert "unavailable" in body.get("detail", "").lower() or "unavailable" in body.get("error", "").lower()


class TestGetNeo4jServiceDegradedFlag:
    """Verify the get_neo4j_service() fast-path when _degraded_mode is set."""

    def test_raises_service_unavailable_in_degraded_mode(self):
        from neo4j.exceptions import ServiceUnavailable
        import src.web.services.neo4j_service as ns

        ns._degraded_mode = True
        with pytest.raises(ServiceUnavailable, match="degraded"):
            ns.get_neo4j_service()

    def test_returns_service_when_not_degraded(self):
        import src.web.services.neo4j_service as ns

        sentinel = MagicMock()
        ns._degraded_mode = False
        ns._neo4j_service = sentinel

        result = ns.get_neo4j_service()
        assert result is sentinel


class TestServicesDependencyDegradedMode:
    """Verify Services.neo4j() dependency raises properly."""

    def test_services_neo4j_raises_when_none(self):
        from neo4j.exceptions import ServiceUnavailable
        from src.web.container import ServiceContainer, Services

        container = ServiceContainer.instance()
        container.neo4j_service = None
        container._started = True

        with pytest.raises(ServiceUnavailable, match="degraded"):
            Services.neo4j()
