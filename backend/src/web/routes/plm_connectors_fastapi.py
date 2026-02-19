"""
PLM Connectors Management API (FastAPI)
Endpoints for managing external PLM system integrations.

Connectors are loaded from environment config (PLM_CONNECTORS JSON) or
default to an empty list. Sync state is tracked in-memory per process.
"""

import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from loguru import logger
from pydantic import BaseModel

from src.web.dependencies import get_api_key
from src.web.utils.responses import Neo4jJSONResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SyncRequest(BaseModel):
    scope: str = "incremental"
    entity_types: List[str] = ["Requirement", "Part"]


class Connector(BaseModel):
    id: str
    name: str
    type: str
    status: str
    url: str
    last_sync: Optional[str] = None


class SyncJob(BaseModel):
    job_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: str
    items_synced: int
    errors: List[str] = []


# ---------------------------------------------------------------------------
# Connector registry — loaded once from environment or config file
# ---------------------------------------------------------------------------
_connectors_lock = threading.Lock()
_connectors: Dict[str, Dict[str, Any]] = {}
_sync_history: Dict[str, List[Dict[str, Any]]] = {}  # connector_id → [SyncJob]


def _load_connectors() -> None:
    """Populate ``_connectors`` from the PLM_CONNECTORS env-var (JSON list).

    Expected format::

        PLM_CONNECTORS='[
          {"id": "teamcenter", "name": "Siemens Teamcenter", "type": "PLM",
           "url": "https://tc.company.com"}
        ]'

    If the env-var is absent or invalid the registry stays empty (no mock data).
    """
    global _connectors
    raw = os.getenv("PLM_CONNECTORS", "").strip()
    if not raw:
        logger.info("PLM_CONNECTORS env not set — connector list is empty")
        return
    try:
        entries = json.loads(raw)
        if not isinstance(entries, list):
            raise ValueError("PLM_CONNECTORS must be a JSON array")
        for entry in entries:
            cid = entry.get("id")
            if not cid:
                continue
            _connectors[cid] = {
                "id": cid,
                "name": entry.get("name", cid),
                "type": entry.get("type", "PLM"),
                "status": "disconnected",
                "url": entry.get("url", ""),
                "last_sync": None,
            }
        logger.info(f"Loaded {len(_connectors)} PLM connector(s) from config")
    except Exception as exc:
        logger.warning(f"Failed to parse PLM_CONNECTORS: {exc}")


# Load on module import
_load_connectors()


def _get_connector(connector_id: str) -> Dict[str, Any]:
    """Return a connector dict or raise 404."""
    with _connectors_lock:
        c = _connectors.get(connector_id)
    if c is None:
        configured = list(_connectors.keys()) if _connectors else ["(none configured)"]
        raise HTTPException(
            status_code=404,
            detail=f"Unknown connector: {connector_id}. Configured: {', '.join(configured)}",
        )
    return dict(c)  # shallow copy


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/connectors", response_class=Neo4jJSONResponse)
async def list_connectors(api_key: str = Depends(get_api_key)):
    """
    Get list of all configured PLM connectors with their current status.

    Connectors are loaded from the ``PLM_CONNECTORS`` environment variable.
    If no connectors are configured, returns an empty list.
    """
    try:
        with _connectors_lock:
            connectors = list(_connectors.values())
        return {"count": len(connectors), "connectors": connectors}
    except Exception as e:
        logger.error(f"Error listing connectors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/connectors/{connector_id}/sync", response_class=Neo4jJSONResponse, status_code=202
)
async def trigger_sync(
    connector_id: str,
    sync_request: SyncRequest = Body(default=SyncRequest()),
    api_key: str = Depends(get_api_key),
):
    """
    Trigger a synchronization job for the specified PLM connector.

    The job is recorded in the in-memory sync history. Actual PLM
    communication requires a connector driver (not yet implemented).
    """
    try:
        connector = _get_connector(connector_id)

        job_id = f"sync_{connector_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        job_record: Dict[str, Any] = {
            "job_id": job_id,
            "connector_id": connector_id,
            "scope": sync_request.scope,
            "entity_types": sync_request.entity_types,
            "status": "pending",
            "started_at": datetime.utcnow().isoformat() + "Z",
            "completed_at": None,
            "items_synced": 0,
            "errors": ["Connector driver not implemented — job recorded only"],
        }

        # Record in history
        with _connectors_lock:
            _sync_history.setdefault(connector_id, []).insert(0, job_record)
            # Cap history at 50 entries
            _sync_history[connector_id] = _sync_history[connector_id][:50]
            _connectors[connector_id]["last_sync"] = job_record["started_at"]

        logger.info(f"Sync job recorded for {connector_id}: {job_id}")

        return {
            "job_id": job_id,
            "connector_id": connector_id,
            "scope": sync_request.scope,
            "entity_types": sync_request.entity_types,
            "status": "pending",
            "started_at": job_record["started_at"],
            "note": "Connector driver not yet implemented — sync request recorded.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering sync for {connector_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connectors/{connector_id}/status", response_class=Neo4jJSONResponse)
async def get_connector_status(connector_id: str, api_key: str = Depends(get_api_key)):
    """
    Get detailed status for a specific connector including real sync history.
    """
    try:
        connector = _get_connector(connector_id)

        with _connectors_lock:
            history = list(_sync_history.get(connector_id, []))

        connector["last_sync"] = history[0] if history else None
        connector["sync_history"] = history[:10]  # last 10

        return connector

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for {connector_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
