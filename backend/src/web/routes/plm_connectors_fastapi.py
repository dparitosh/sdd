"""
PLM Connectors Management API (FastAPI)
Endpoints for managing external PLM system integrations
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from loguru import logger
from pydantic import BaseModel

from src.web.dependencies import get_api_key
from src.web.app_fastapi import Neo4jJSONResponse

router = APIRouter()


# Request/Response models
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


def get_available_connectors() -> List[Dict[str, Any]]:
    """Get list of configured PLM connectors"""
    # In production, this would read from config/database
    # For now, return configured connectors with mock status
    connectors = [
        {
            "id": "teamcenter",
            "name": "Siemens Teamcenter",
            "type": "PLM",
            "status": "disconnected",  # Requires configuration
            "url": "https://teamcenter.example.com",
            "last_sync": None,
        },
        {
            "id": "windchill",
            "name": "PTC Windchill",
            "type": "PLM",
            "status": "disconnected",  # Requires configuration
            "url": "https://windchill.example.com",
            "last_sync": None,
        },
    ]

    return connectors


@router.get("/connectors", response_class=Neo4jJSONResponse)
async def list_connectors(api_key: str = Depends(get_api_key)):
    """
    Get list of all configured PLM connectors with their status.

    Returns:
        {
            "connectors": [
                {
                    "id": "teamcenter",
                    "name": "Siemens Teamcenter",
                    "type": "PLM",
                    "status": "connected|disconnected|error",
                    "url": "https://tc.company.com",
                    "last_sync": "2025-01-15T10:30:00Z"
                }
            ]
        }
    """
    try:
        connectors = get_available_connectors()
        return {"count": len(connectors), "connectors": connectors}
    except Exception as e:
        logger.error(f"Error listing connectors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connectors/{connector_id}/sync", response_class=Neo4jJSONResponse, status_code=202)
async def trigger_sync(
    connector_id: str,
    sync_request: SyncRequest = Body(default=SyncRequest()),
    api_key: str = Depends(get_api_key)
):
    """
    Trigger a synchronization job for the specified PLM connector.

    Request Body (optional):
        {
            "scope": "full|incremental",
            "entity_types": ["Requirement", "Part", "Document"]
        }

    Returns:
        {
            "job_id": "sync_tc_20250115_103045",
            "connector_id": "teamcenter",
            "status": "started",
            "started_at": "2025-01-15T10:30:45Z"
        }
    """
    try:
        if connector_id not in ["teamcenter", "windchill"]:
            raise HTTPException(status_code=404, detail=f"Unknown connector: {connector_id}")

        # Generate job ID
        job_id = f"sync_{connector_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Start sync job (async)
        # In production, would trigger actual connector sync
        result = {
            "job_id": job_id,
            "connector_id": connector_id,
            "scope": sync_request.scope,
            "entity_types": sync_request.entity_types,
            "status": "started",
            "started_at": datetime.utcnow().isoformat() + "Z",
        }
        logger.info(f"Started {connector_id} sync job: {job_id}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering sync for {connector_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connectors/{connector_id}/status", response_class=Neo4jJSONResponse)
async def get_connector_status(
    connector_id: str,
    api_key: str = Depends(get_api_key)
):
    """
    Get detailed status for a specific connector including recent sync history.

    Returns:
        {
            "id": "teamcenter",
            "name": "Siemens Teamcenter",
            "status": "connected",
            "url": "https://tc.company.com",
            "last_sync": {
                "job_id": "sync_tc_20250115_103045",
                "started_at": "2025-01-15T10:30:45Z",
                "completed_at": "2025-01-15T10:35:12Z",
                "status": "completed",
                "items_synced": 156,
                "errors": []
            },
            "sync_history": [...]
        }
    """
    try:
        if connector_id not in ["teamcenter", "windchill"]:
            raise HTTPException(status_code=404, detail=f"Unknown connector: {connector_id}")

        connectors = get_available_connectors()
        connector = next((c for c in connectors if c["id"] == connector_id), None)

        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found")

        # Add sync history (mock for now - should come from database)
        connector["last_sync"] = {
            "job_id": f"sync_{connector_id}_20250115_103045",
            "started_at": "2025-01-15T10:30:45Z",
            "completed_at": "2025-01-15T10:35:12Z",
            "status": "completed",
            "items_synced": 156,
            "errors": [],
        }

        connector["sync_history"] = [
            {
                "job_id": f"sync_{connector_id}_20250115_103045",
                "started_at": "2025-01-15T10:30:45Z",
                "completed_at": "2025-01-15T10:35:12Z",
                "status": "completed",
                "items_synced": 156,
            },
            {
                "job_id": f"sync_{connector_id}_20250114_093022",
                "started_at": "2025-01-14T09:30:22Z",
                "completed_at": "2025-01-14T09:34:58Z",
                "status": "completed",
                "items_synced": 142,
            },
        ]

        return connector

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for {connector_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
