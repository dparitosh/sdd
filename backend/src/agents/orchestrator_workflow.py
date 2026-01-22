"""
Multi-Agent Orchestration Workflow using LangGraph
Coordinates specialized agents (MBSE, PLM, Simulation, Compliance) for complex engineering tasks

Now also supports Azure AI Baseline Orchestrator pattern (vendor-neutral).
"""

import operator
from typing import Annotated, Literal, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from loguru import logger

from ..agentic import (
    BaselineOrchestrator,
    KeywordPlanner,
    SimpleReflector,
    SingleToolAgent,
)
from ..agentic.adapters import MBSEToolsAdapter
from .langgraph_agent import MBSETools
from .plm_agent import PLMAgent
from .simulation_agent import SimulationAgent


# ============================================================================
# STATE DEFINITION
# ============================================================================


class EngineeringState(TypedDict):
    """
    Shared state across all specialized agents
    Enables coordination and information flow between agents
    """

    # Input
    user_query: str
    task_type: Literal[
        "traceability", "impact_analysis", "requirement_check", "bom_sync"
    ]

    # MBSE Agent outputs
    requirement_id: str | None
    artifact_details: dict | None
    traceability_data: dict | None

    # PLM Agent outputs
    affected_parts: list[dict]
    bom_data: dict | None
    change_impact: dict | None

    # Simulation Agent outputs
    simulation_parameters: dict | None
    validation_results: dict | None
    simulation_summary: dict | None

    # Compliance Agent outputs
    compliance_status: dict | None
    violations: list[dict]
    recommendations: list[str]

    # Shared
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_action: str
    error: str | None


# ============================================================================
# AGENT NODE FUNCTIONS
# ============================================================================


async def mbse_agent_node(state: EngineeringState) -> dict:
    """
    MBSE Agent: Query requirements, artifacts, and traceability
    Uses MBSETools to interact with Neo4j knowledge graph
    """
    logger.info("🔍 MBSE Agent: Analyzing query and searching knowledge graph")

    tools = MBSETools()
    user_query = state["user_query"]

    try:
        # Search for relevant artifacts
        search_results = tools.search_artifacts(user_query, limit=10)
        logger.debug(f"Found artifacts: {search_results[:100]}...")

        # Get traceability if requirement found
        traceability_data = None
        if "requirement" in user_query.lower():
            try:
                # get_traceability might fail if not fully implemented in tools, wrap safely
                traceability_data = tools.get_traceability(source_type="Requirement")
            except:
                traceability_data = {"note": "Traceability fetch failed or not applicable"}

        messages = [
            AIMessage(
                content=f"MBSE Agent: Found relevant artifacts in knowledge graph"
            )
        ]

        # Determine next step based on task type
        task = state.get("task_type", "traceability")
        next_step = END
        if task == "impact_analysis" or task == "bom_sync":
            next_step = "plm_agent"
        elif task == "requirement_check":
            next_step = "simulation_agent"

        return {
            "artifact_details": {"search_results": search_results},
            "traceability_data": traceability_data,
            "messages": messages,
            "next_action": next_step,
        }

    except Exception as e:
        logger.error(f"MBSE Agent error: {e}")
        return {
            "error": f"MBSE Agent failed: {str(e)}",
            "messages": [AIMessage(content=f"MBSE Agent encountered error: {str(e)}")],
            "next_action": END
        }


async def plm_agent_node(state: EngineeringState) -> dict:
    """PLM Agent: Interact with Teamcenter/Windchill"""
    logger.info("⚙️ PLM Agent: Checking component status and BOM")
    
    agent = PLMAgent(system_type="teamcenter")
    
    try:
        # Extract IDs from state['artifact_details'] if available, else mock
        part_ids = ["000123", "000456"] 
        
        # Async call to agent
        availability = await agent.check_part_availability(part_ids)
        
        messages = [AIMessage(content=f"PLM Agent: Checked part status in Teamcenter. Results: {len(availability)} parts.")]
        
        return {
            "affected_parts": [{"id": pid, "status": "Released"} for pid in part_ids], # partial mock for now
            "messages": messages,
            "next_action": END
        }
    except Exception as e:
        return {"error": str(e), "next_action": END}


async def simulation_agent_node(state: EngineeringState) -> dict:
    """Simulation Agent: Run analysis"""
    logger.info("🧪 Simulation Agent: Validating requirements")
    
    agent = SimulationAgent()
    params = agent.get_simulation_parameters("Model-X")
    
    # Run simulation (Fea)
    result = await agent.run_simulation("fea", params)
    
    return {
        "simulation_parameters": params,
        "simulation_summary": result,
        "messages": [AIMessage(content=f"Simulation Agent: Simulation complete. Status: {result.get('status')}")],
        "next_action": END
    }


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_engineering_workflow():
    """Create the multi-agent workflow graph"""
    workflow = StateGraph(EngineeringState)

    # Add nodes
    workflow.add_node("mbse_agent", mbse_agent_node)
    workflow.add_node("plm_agent", plm_agent_node)
    workflow.add_node("simulation_agent", simulation_agent_node)

    # set entry point
    workflow.set_entry_point("mbse_agent")

    # Add conditional edges based on next_action
    def router(state):
        return state["next_action"]

    workflow.add_conditional_edges(
        "mbse_agent",
        router,
        {
            "plm_agent": "plm_agent",
            "simulation_agent": "simulation_agent",
            END: END
        }
    )
    
    workflow.add_edge("plm_agent", END)
    workflow.add_edge("simulation_agent", END)

    return workflow.compile()


async def execute_engineering_workflow(user_query: str, task_type: str = "impact_analysis") -> dict:
    """Execute the multi-agent workflow"""
    workflow = create_engineering_workflow()
    
    initial_state = {
        "user_query": user_query,
        "task_type": task_type,
        "messages": [HumanMessage(content=user_query)],
        "next_action": "mbse_agent",
        
        # Initialize other fields to None/Empty
        "requirement_id": None, "artifact_details": None, "traceability_data": None,
        "affected_parts": [], "bom_data": None, "change_impact": None,
        "simulation_parameters": None, "validation_results": None, "simulation_summary": None,
        "compliance_status": None, "violations": [], "recommendations": [],
        "error": None
    }
    
    app = workflow.compile()
    result = await app.ainvoke(initial_state)
    return result


# ============================================================================
# BASELINE ORCHESTRATOR (AZURE AI PATTERN)
# ============================================================================

def create_baseline_orchestrator() -> BaselineOrchestrator:
    """Create a baseline orchestrator aligned with Azure AI agentic patterns."""
    tools = MBSETools()
    tool_registry = MBSEToolsAdapter(tools_api=tools)
    planner = KeywordPlanner()
    reflector = SimpleReflector()

    mbse_agent = SingleToolAgent(name="mbse_worker", planner=planner)

    orchestrator = BaselineOrchestrator(
        tool_registry=tool_registry,
        planner=planner,
        reflector=reflector,
        agents=[mbse_agent],
        max_retries=1,
    )
    return orchestrator


def execute_baseline_workflow(user_query: str) -> str:
    """Execute a goal using the baseline orchestrator."""
    logger.info(f"🚀 Executing baseline orchestrator workflow for: {user_query}")
    orchestrator = create_baseline_orchestrator()

    try:
        response = orchestrator.run(user_query)
        logger.info("✓ Baseline workflow completed successfully")
        return response
    except Exception as e:
        logger.error(f"Baseline workflow failed: {e}")
        return f"Error: {e}"


# ============================================================================
# EXAMPLE USAGE
# ============================================================================


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"

    if mode == "langgraph":
        # Original LangGraph multi-agent workflow
        result = execute_engineering_workflow(
            user_query="What happens if I change the brake caliper material to titanium?",
            task_type="impact_analysis",
        )

        print("\n" + "=" * 80)
        print("LANGGRAPH WORKFLOW EXECUTION RESULTS")
        print("=" * 80)
        print(f"\nQuery: {result['user_query']}")
        print(f"Task Type: {result['task_type']}")
        print(f"\n--- MBSE Agent Results ---")
        print(f"Artifacts Found: {result.get('artifact_details', 'None')}")
        print(f"\n--- PLM Agent Results ---")
        print(f"Affected Parts: {len(result.get('affected_parts', []))}")
        print(f"Change Impact: {result.get('change_impact', 'None')}")
        print(f"\n--- Simulation Agent Results ---")
        print(f"Validation: {result.get('validation_results', 'None')}")
        print(f"\n--- Compliance Agent Results ---")
        print(f"Compliance Status: {result.get('compliance_status', 'None')}")
        print(f"Recommendations: {result.get('recommendations', [])}")
        print(f"\nError: {result.get('error', 'None')}")
        print("=" * 80)

    else:
        # Baseline orchestrator (Azure AI pattern, vendor-neutral)
        query = "Show me traceability from requirements to design elements"
        response = execute_baseline_workflow(query)

        print("\n" + "=" * 80)
        print("BASELINE ORCHESTRATOR RESULTS (Azure AI Pattern)")
        print("=" * 80)
        print(f"\nQuery: {query}")
        print(f"\nResponse:\n{response}")
        print("\n" + "=" * 80)
