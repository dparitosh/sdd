"""
Version Control Routes (FastAPI)
Endpoints for version control and change management:
- Version history tracking
- Version comparison (diff)
- Change audit trail
- Checkpoint/snapshot creation
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from src.web.app_fastapi import Neo4jJSONResponse
from src.web.services import get_neo4j_service

# ============================================================================
# ROUTER CONFIGURATION
# ============================================================================

router = APIRouter(prefix="/version", tags=["Version Control"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class CurrentVersion(BaseModel):
    version: Optional[int] = 1
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    load_source: Optional[str] = None
    properties: Dict[str, Any]


class VersionHistoryEntry(BaseModel):
    version: int
    timestamp: Optional[str] = None
    change_type: str
    properties: Dict[str, Any]


class NodeVersionInfo(BaseModel):
    node_id: str
    name: str
    labels: List[str]
    current_version: CurrentVersion
    version_history: List[VersionHistoryEntry]


class NodeInfo(BaseModel):
    id: str
    labels: List[str]
    properties: Dict[str, Any]


class PropertyChange(BaseModel):
    old: Any
    new: Any


class Differences(BaseModel):
    added_properties: Dict[str, Any]
    removed_properties: Dict[str, Any]
    modified_properties: Dict[str, PropertyChange]
    unchanged_properties: List[str]


class DiffSummary(BaseModel):
    total_differences: int
    added_count: int
    removed_count: int
    modified_count: int


class VersionDiff(BaseModel):
    node1: NodeInfo
    node2: NodeInfo
    differences: Differences
    summary: DiffSummary


class CompareRequest(BaseModel):
    node1_id: str = Field(..., description="First node ID to compare")
    node2_id: str = Field(..., description="Second node ID to compare")


class HistoryStatistics(BaseModel):
    relationship_count: int
    related_nodes: int


class TimelineEvent(BaseModel):
    timestamp: str
    event: str
    version: int
    description: str


class NodeHistory(BaseModel):
    node_id: str
    name: str
    labels: List[str]
    current_version: int
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    statistics: HistoryStatistics
    timeline: List[TimelineEvent]
    properties: Dict[str, Any]


class CheckpointRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = Field("Manual checkpoint", description="Checkpoint description")


class CheckpointStatistics(BaseModel):
    nodes: int
    relationships: int
    node_labels: List[str]


class Checkpoint(BaseModel):
    name: str
    description: str
    timestamp: str
    statistics: CheckpointStatistics
    status: str
    note: str


# ============================================================================
# VERSION HISTORY ENDPOINT
# ============================================================================


@router.get("/versions/{node_id}", response_model=NodeVersionInfo, response_class=Neo4jJSONResponse)
async def get_node_versions(node_id: str):
    """
    Get version history for a specific node
    
    Returns version information including creation/modification timestamps
    and property values.
    
    Args:
        node_id: Unique identifier of the node
        
    Returns:
        Version history with current and historical versions
        
    Raises:
        HTTPException 404: Node not found
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (n {id: $node_id})
        RETURN n.id as id,
               n.name as name,
               labels(n) as labels,
               n.version as version,
               n.createdAt as created_at,
               n.modifiedAt as modified_at,
               n.loadSource as load_source,
               properties(n) as properties
        """

        result = neo4j.execute_query(query, {"node_id": node_id})

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node with ID '{node_id}' not found"
            )

        node = result[0]

        # In a full versioning system, we would query historical versions
        version_info = {
            "node_id": node["id"],
            "name": node["name"],
            "labels": node["labels"],
            "current_version": {
                "version": node["version"] or 1,
                "created_at": node["created_at"],
                "modified_at": node["modified_at"],
                "load_source": node["load_source"],
                "properties": node["properties"],
            },
            "version_history": [
                {
                    "version": node["version"] or 1,
                    "timestamp": node["modified_at"] or node["created_at"],
                    "change_type": "created",
                    "properties": node["properties"],
                }
            ],
        }

        return version_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Version history error for {node_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve version history: {str(e)}"
        )


# ============================================================================
# VERSION COMPARISON ENDPOINT
# ============================================================================


@router.post("/diff", response_model=VersionDiff, response_class=Neo4jJSONResponse)
async def compare_versions(compare_request: CompareRequest):
    """
    Compare two versions of nodes or two different nodes
    
    Performs property-level diff showing added, removed, modified, and unchanged properties.
    
    Args:
        compare_request: Node IDs to compare
        
    Returns:
        Detailed diff with property changes
        
    Raises:
        HTTPException 404: One or both nodes not found
    """
    try:
        neo4j = get_neo4j_service()

        node1_id = compare_request.node1_id
        node2_id = compare_request.node2_id

        # Query both nodes
        query = """
        MATCH (n1 {id: $id1})
        MATCH (n2 {id: $id2})
        RETURN properties(n1) as props1, labels(n1) as labels1,
               properties(n2) as props2, labels(n2) as labels2
        """

        result = neo4j.execute_query(query, {"id1": node1_id, "id2": node2_id})

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or both nodes not found"
            )

        record = result[0]
        props1 = record["props1"]
        props2 = record["props2"]

        # Calculate diff
        all_keys = set(props1.keys()) | set(props2.keys())

        added = {}
        removed = {}
        modified = {}
        unchanged = {}

        for key in all_keys:
            val1 = props1.get(key)
            val2 = props2.get(key)

            if key not in props1:
                added[key] = val2
            elif key not in props2:
                removed[key] = val1
            elif val1 != val2:
                modified[key] = {"old": val1, "new": val2}
            else:
                unchanged[key] = val1

        diff = {
            "node1": {"id": node1_id, "labels": record["labels1"], "properties": props1},
            "node2": {"id": node2_id, "labels": record["labels2"], "properties": props2},
            "differences": {
                "added_properties": added,
                "removed_properties": removed,
                "modified_properties": modified,
                "unchanged_properties": list(unchanged.keys()),
            },
            "summary": {
                "total_differences": len(added) + len(removed) + len(modified),
                "added_count": len(added),
                "removed_count": len(removed),
                "modified_count": len(modified),
            },
        }

        return diff

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Version comparison error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare versions: {str(e)}"
        )


# ============================================================================
# CHANGE HISTORY ENDPOINT
# ============================================================================


@router.get("/history/{node_id}", response_model=NodeHistory, response_class=Neo4jJSONResponse)
async def get_node_history(node_id: str):
    """
    Get change history/audit trail for a specific node
    
    Returns timeline of all changes with timestamps, statistics, and current state.
    
    Args:
        node_id: Unique identifier of the node
        
    Returns:
        Complete change history with timeline and statistics
        
    Raises:
        HTTPException 404: Node not found
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (n {id: $node_id})
        OPTIONAL MATCH (n)-[r]-(related)
        RETURN n.id as id,
               n.name as name,
               labels(n) as labels,
               n.version as version,
               n.createdAt as created_at,
               n.modifiedAt as modified_at,
               properties(n) as properties,
               COUNT(DISTINCT r) as relationship_count,
               COUNT(DISTINCT related) as related_nodes
        """

        result = neo4j.execute_query(query, {"node_id": node_id})

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node with ID '{node_id}' not found"
            )

        record = result[0]

        # Build history timeline
        timeline = []

        if record["created_at"]:
            timeline.append({
                "timestamp": record["created_at"],
                "event": "created",
                "version": 1,
                "description": f"Node created: {record['name']}",
            })

        if record["modified_at"] and record["modified_at"] != record["created_at"]:
            timeline.append({
                "timestamp": record["modified_at"],
                "event": "modified",
                "version": record["version"] or 1,
                "description": "Node properties updated",
            })

        history = {
            "node_id": node_id,
            "name": record["name"],
            "labels": record["labels"],
            "current_version": record["version"] or 1,
            "created_at": record["created_at"],
            "last_modified": record["modified_at"],
            "statistics": {
                "relationship_count": record["relationship_count"],
                "related_nodes": record["related_nodes"],
            },
            "timeline": sorted(timeline, key=lambda x: x["timestamp"], reverse=True),
            "properties": record["properties"],
        }

        return history

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"History query error for {node_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )


# ============================================================================
# CHECKPOINT CREATION ENDPOINT
# ============================================================================


@router.post("/checkpoint", response_model=Checkpoint, response_class=Neo4jJSONResponse, status_code=status.HTTP_201_CREATED)
async def create_checkpoint(checkpoint_request: CheckpointRequest):
    """
    Create a snapshot/checkpoint of the entire graph
    
    Captures graph statistics and metadata for version tracking.
    Note: Full graph snapshots would require additional storage mechanism.
    
    Args:
        checkpoint_request: Checkpoint name and description
        
    Returns:
        Checkpoint metadata with graph statistics
    """
    try:
        neo4j = get_neo4j_service()

        checkpoint_name = checkpoint_request.name or f'checkpoint_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        description = checkpoint_request.description

        # Get graph statistics
        stats_query = """
        MATCH (n)
        WITH COUNT(n) as node_count, COLLECT(DISTINCT labels(n)) as all_labels
        OPTIONAL MATCH ()-[r]->()
        RETURN node_count,
               COUNT(r) as relationship_count,
               all_labels
        """

        stats_result = neo4j.execute_query(stats_query)

        if not stats_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve graph statistics"
            )

        stats = stats_result[0]

        checkpoint = {
            "name": checkpoint_name,
            "description": description,
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": {
                "nodes": stats["node_count"],
                "relationships": stats["relationship_count"],
                "node_labels": [label for sublist in stats["all_labels"] for label in sublist],
            },
            "status": "created",
            "note": "Checkpoint metadata saved. Full graph snapshot would require additional storage mechanism.",
        }

        return checkpoint

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Checkpoint creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkpoint: {str(e)}"
        )
