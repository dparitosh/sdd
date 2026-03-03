"""
Multi-Agent Orchestration Routes (FastAPI)
Endpoints for interacting with the Engineering Agent Orchestrator
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from loguru import logger

from src.agents.orchestrator_workflow import execute_engineering_workflow
from src.web.utils.responses import Neo4jJSONResponse
from src.web.dependencies import get_api_key

# ============================================================================
# ROUTER CONFIGURATION
# ============================================================================

router = APIRouter(prefix="/agents", tags=["AI Agents & Orchestration"], dependencies=[Depends(get_api_key)])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class AgentRequest(BaseModel):
    query: str = Field(..., description="Natural language query for the engineering agents")
    task_type: Optional[str] = Field("impact_analysis", description="Type of task (traceability, impact_analysis, requirement_check, bom_sync)")
    mode: Optional[str] = Field("langgraph", description="Orchestration mode: 'langgraph' or 'baseline'")

class AgentMessage(BaseModel):
    role: str
    content: str
    type: str

class AgentResponse(BaseModel):
    status: str
    messages: List[Dict[str, Any]]
    final_state: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================================
# ROUTES
# ============================================================================

@router.post("/orchestrator/run", response_model=AgentResponse)
async def run_orchestrator(request: AgentRequest):
    """
    Execute the multi-agent engineering workflow.
    
    Coordinating agents:
    - MBSE Agent (Knowledge Graph)
    - PLM Agent (Teamcenter/Windchill)
    - Simulation Agent (Parameters/Validation)
    - Compliance Agent (Regulations)
    """
    logger.info(f"🤖 Orchestrator received request: {request.query} [{request.task_type}]")
    
    try:
        # Execute workflow
        # Now async to support MoSSEC/OSLC TRS operations
        result = await execute_engineering_workflow(request.query, request.task_type)
        
        # Format messages for response
        formatted_messages = []
        if "messages" in result:
            for msg in result["messages"]:
                formatted_messages.append({
                    "role": "ai" if msg.type == "ai" else "user",
                    "content": msg.content,
                    "type": msg.type
                })
        
        return {
            "status": "success",
            "messages": formatted_messages,
            "final_state": {k: v for k, v in result.items() if k != "messages"},
            "error": result.get("error")
        }
        
    except Exception as e:
        # Log full traceback for easier debugging
        logger.exception("Orchestrator endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SEMANTIC SEARCH & INSIGHT (RAG pipeline)
# ============================================================================

from src.agents.semantic_agent import SemanticAgent

_semantic_agent: SemanticAgent | None = None


def _get_semantic_agent() -> SemanticAgent:
    global _semantic_agent
    if _semantic_agent is None:
        _semantic_agent = SemanticAgent()
    return _semantic_agent


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    top_k: int = Field(10, ge=1, le=100)
    expand: bool = Field(True, description="Include 2-hop Neo4j expansion")
    threshold: float = Field(0.5, ge=0.0, le=1.0)


class SemanticInsightRequest(BaseModel):
    question: str = Field(..., description="Natural language question for RAG synthesis")
    top_k: int = Field(5, ge=1, le=50)


@router.post("/semantic/search")
async def semantic_search(request: SemanticSearchRequest):
    """Semantic vector search over the knowledge graph.

    Embeds the query → kNN search in OpenSearch → optional 2-hop
    Neo4j expansion.  Falls back to Neo4j full-text search when
    OpenSearch is unreachable.
    """
    agent = _get_semantic_agent()
    try:
        result = agent.semantic_search(
            query=request.query,
            top_k=request.top_k,
            expand=request.expand,
            threshold=request.threshold,
        )
        return {"status": "success", "data": result}
    except Exception as exc:
        logger.exception("Semantic search failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/semantic/insight")
async def semantic_insight(request: SemanticInsightRequest):
    """Full RAG pipeline: search → LLM synthesis → markdown answer + sources."""
    agent = _get_semantic_agent()
    try:
        result = agent.semantic_insight(
            question=request.question,
            top_k=request.top_k,
        )
        return {"status": "success", "data": result}
    except Exception as exc:
        logger.exception("Semantic insight failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
