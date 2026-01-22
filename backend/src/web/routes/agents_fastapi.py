"""
Multi-Agent Orchestration Routes (FastAPI)
Endpoints for interacting with the Engineering Agent Orchestrator
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from loguru import logger

from src.agents.orchestrator_workflow import execute_engineering_workflow
from src.web.app_fastapi import Neo4jJSONResponse

# ============================================================================
# ROUTER CONFIGURATION
# ============================================================================

router = APIRouter(prefix="/agents", tags=["AI Agents & Orchestration"])


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
        logger.error(f"Orchestrator endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
