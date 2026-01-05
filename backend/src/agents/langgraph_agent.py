"""
LangGraph-based AI Agent Framework for MBSE Knowledge Graph
Implements reasoning, tool-use, and orchestration capabilities
"""

import json
import operator
import os
from typing import Annotated, Any, Literal, Optional, TypedDict

import requests
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from loguru import logger
from pydantic import SecretStr


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, default=str)

# ============================================================================
# STATE DEFINITION
# ============================================================================


class AgentState(TypedDict):
    """State for the agent graph"""

    messages: Annotated[list[BaseMessage], operator.add]
    current_task: str
    reasoning_steps: list[str]
    tool_results: dict
    next_action: str
    error: Optional[str]


# ============================================================================
# TOOLS - API Wrappers
# ============================================================================


class MBSETools:
    """Tools for interacting with MBSE Knowledge Graph API"""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        env_base_url = os.getenv("API_BASE_URL") or os.getenv("VITE_API_BASE_URL")
        backend_host = os.getenv("BACKEND_HOST")
        backend_port = os.getenv("BACKEND_PORT")

        if not base_url and not env_base_url and backend_host and backend_port:
            env_base_url = f"http://{backend_host}:{backend_port}"

        resolved_base_url = base_url or env_base_url
        if not resolved_base_url:
            raise ValueError(
                "Missing API base URL configuration. Set API_BASE_URL in .env (recommended) "
                "or set BACKEND_HOST and BACKEND_PORT."
            )
        self.base_url = resolved_base_url
        self.api_v1 = f"{resolved_base_url}/api/v1"
        self.api_core = f"{resolved_base_url}/api"

        # FastAPI protects most endpoints via X-API-Key when API_KEY is configured.
        # Default to env API_KEY so agents work in secured deployments.
        resolved_api_key = api_key or os.getenv("API_KEY")
        self.session = requests.Session()
        if resolved_api_key:
            self.session.headers.update({"X-API-Key": resolved_api_key})

    def search_artifacts(self, query: str, limit: int = 10) -> str:
        """Search for artifacts by name or description"""
        try:
            response = self.session.post(
                f"{self.api_core}/search", json={"name": query, "limit": limit}
            )
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except requests.RequestException as e:
            return f"Error searching artifacts: {str(e)}"

    def get_artifact_details(self, artifact_type: str, artifact_id: str) -> str:
        """Get detailed information about a specific artifact"""
        try:
            response = self.session.get(
                f"{self.api_core}/artifacts/{artifact_type}/{artifact_id}"
            )
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except requests.RequestException as e:
            return f"Error getting artifact details: {str(e)}"

    def get_traceability(
        self,
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
        depth: int = 2,
    ) -> str:
        """Get traceability matrix between artifacts"""
        try:
            params: dict[str, Any] = {"depth": depth}
            if source_type:
                params["source_type"] = source_type
            if target_type:
                params["target_type"] = target_type
            response = self.session.get(f"{self.api_v1}/traceability", params=params)
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except requests.RequestException as e:
            return f"Error getting traceability: {str(e)}"

    def get_impact_analysis(self, node_id: str, depth: int = 3) -> str:
        """Analyze change impact for a node"""
        try:
            response = self.session.get(
                f"{self.api_v1}/impact/{node_id}", params={"depth": depth}
            )
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except requests.RequestException as e:
            return f"Error analyzing impact: {str(e)}"

    def get_parameters(self, class_name: Optional[str] = None, limit: int = 20) -> str:
        """Extract design parameters"""
        try:
            params: dict[str, Any] = {"limit": limit}
            if class_name:
                params["class"] = class_name
            response = self.session.get(f"{self.api_v1}/parameters", params=params)
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except requests.RequestException as e:
            return f"Error getting parameters: {str(e)}"

    def execute_cypher(self, query: str) -> str:
        """Execute custom Cypher query"""
        try:
            response = self.session.post(
                f"{self.api_core}/cypher", json={"query": query}
            )
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except requests.RequestException as e:
            return f"Error executing Cypher: {str(e)}"

    def get_statistics(self) -> str:
        """Get database statistics"""
        try:
            response = self.session.get(f"{self.api_core}/stats")
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except requests.RequestException as e:
            return f"Error getting statistics: {str(e)}"


# ============================================================================
# AGENT NODES
# ============================================================================


class MBSEAgent:
    """LangGraph-based MBSE reasoning agent"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        env_base_url = os.getenv("API_BASE_URL") or os.getenv("VITE_API_BASE_URL")
        backend_host = os.getenv("BACKEND_HOST")
        backend_port = os.getenv("BACKEND_PORT")
        if not base_url and not env_base_url and backend_host and backend_port:
            env_base_url = f"http://{backend_host}:{backend_port}"

        resolved_base_url = base_url or env_base_url
        if not resolved_base_url:
            raise ValueError(
                "Missing API base URL configuration. Set API_BASE_URL in .env (recommended) "
                "or set BACKEND_HOST and BACKEND_PORT."
            )

        self.tools_api = MBSETools(resolved_base_url)
        secret_api_key = SecretStr(api_key) if api_key else None
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7, api_key=secret_api_key)

        # Create LangChain tools
        self.tools = [
            Tool(
                name="search_artifacts",
                func=self.tools_api.search_artifacts,
                description="Search for artifacts (classes, packages, requirements) by name. Input: query string, Returns: JSON list of matching artifacts",
            ),
            Tool(
                name="get_artifact_details",
                func=self.tools_api.get_artifact_details,
                description="Get detailed information about a specific artifact. Input: artifact_type (Class/Package/Requirement), artifact_id, Returns: JSON with full details",
            ),
            Tool(
                name="get_traceability",
                func=self.tools_api.get_traceability,
                description="Get traceability matrix between artifacts (e.g., requirements to design). Input: source_type, target_type, depth, Returns: JSON traceability matrix",
            ),
            Tool(
                name="get_impact_analysis",
                func=self.tools_api.get_impact_analysis,
                description="Analyze change impact for a node showing upstream and downstream dependencies. Input: node_id, depth, Returns: JSON impact analysis",
            ),
            Tool(
                name="get_parameters",
                func=self.tools_api.get_parameters,
                description="Extract design parameters from classes. Input: class_name (optional), limit, Returns: JSON list of parameters",
            ),
            Tool(
                name="execute_cypher",
                func=self.tools_api.execute_cypher,
                description="Execute custom Cypher query for complex analysis. Input: cypher query string, Returns: JSON query results",
            ),
            Tool(
                name="get_statistics",
                func=self.tools_api.get_statistics,
                description="Get database statistics (node counts, relationships, types). Input: none, Returns: JSON statistics",
            ),
        ]

        # Use the prebuilt React agent pattern
        self.graph = create_react_agent(self.llm, self.tools)

    def _understand_task(self, state: AgentState) -> AgentState:
        """Understand and categorize the user's task"""
        messages = state["messages"]
        last_message = _content_to_text(messages[-1].content) if messages else ""

        # Use LLM to understand task category
        system_prompt = """You are an MBSE (Model-Based Systems Engineering) expert assistant.
Analyze the user's request and categorize it into one of these task types:
- search: Find artifacts by name/description
- traceability: Trace requirements to design or vice versa
- impact: Analyze change impact
- parameters: Extract design parameters
- query: Complex custom query
- statistics: Get overview statistics
- other: General question

Respond with just the category and a brief explanation."""

        understanding_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=last_message),
        ]

        response = self.llm.invoke(understanding_messages)

        response_text = _content_to_text(response.content)

        logger.info(f"Task understanding: {response_text}")

        return {
            **state,
            "current_task": response_text,
            "reasoning_steps": [f"Understanding: {response_text}"],
        }

    def _plan_steps(self, state: AgentState) -> AgentState:
        """Plan the steps needed to complete the task"""
        task = state["current_task"]

        # Use LLM with ReAct pattern to plan
        system_prompt = """You are planning how to solve an MBSE task.
Available tools:
- search_artifacts: Search for classes, packages, requirements
- get_artifact_details: Get full details of an artifact
- get_traceability: Get requirements-to-design traceability
- get_impact_analysis: Analyze change impact
- get_parameters: Extract design parameters
- execute_cypher: Run custom Neo4j queries
- get_statistics: Get database overview

Based on the task, decide which tool to use next. If you have enough information, say "RESPOND"."""

        planning_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Task: {task}\nWhat should I do next?"),
        ]

        response = self.llm.invoke(planning_messages)
        next_action = _content_to_text(response.content)

        logger.info(f"Planning: {next_action}")

        state["reasoning_steps"].append(f"Planning: {next_action}")
        state["next_action"] = next_action

        return state

    def _should_use_tool(self, state: AgentState) -> Literal["execute", "respond"]:
        """Decide if we should execute a tool or respond"""
        next_action = state.get("next_action", "")

        if "RESPOND" in next_action.upper():
            return "respond"

        # Check if any tool name is mentioned
        for tool in self.tools:
            if tool.name in next_action.lower():
                return "execute"

        return "respond"

    def _execute_tool(self, state: AgentState) -> AgentState:
        """Execute the selected tool"""
        next_action = state["next_action"]

        # Parse tool name and arguments from LLM response
        tool_name = None
        tool_func = None

        for tool in self.tools:
            if tool.name in next_action.lower():
                tool_name = tool.name
                tool_func = tool.func
                break

        if not tool_name or not tool_func:
            state["error"] = "Could not determine which tool to use"
            return state

        # Execute tool directly
        try:
            # For simplified execution, call tool function directly
            result = tool_func()

            state["tool_results"][tool_name] = result
            state["reasoning_steps"].append(
                f"Executed {tool_name}: Got {len(str(result))} chars of data"
            )

            logger.info(f"Tool execution: {tool_name} succeeded")
        except Exception as e:  # noqa: BLE001 pylint: disable=broad-exception-caught
            state["error"] = str(e)
            logger.error(f"Tool execution failed: {e}")

        return state

    def _reason_about_results(self, state: AgentState) -> AgentState:
        """Reason about tool execution results"""
        tool_results = state["tool_results"]

        if not tool_results:
            return state

        # Use LLM to reason about results
        system_prompt = """You are analyzing the results from MBSE tools.
Decide if you have enough information to answer the user's question, or if you need to use more tools."""

        results_summary = json.dumps(tool_results, indent=2)[:1000]  # Limit size

        reasoning_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"Results so far:\n{results_summary}\n\nDo we have enough information?"
            ),
        ]

        response = self.llm.invoke(reasoning_messages)

        state["reasoning_steps"].append(f"Reasoning: {response.content}")

        return state

    def _should_continue(self, state: AgentState) -> Literal["continue", "respond"]:
        """Decide if we should continue gathering information or respond"""
        reasoning = state["reasoning_steps"][-1] if state["reasoning_steps"] else ""

        if "enough" in reasoning.lower() or len(state["tool_results"]) >= 3:
            return "respond"

        return "continue"

    def _generate_response(self, state: AgentState) -> AgentState:
        """Generate final response to user"""
        messages = state["messages"]
        tool_results = state["tool_results"]
        reasoning_steps = state["reasoning_steps"]

        # Create comprehensive context for response
        context = f"""
    User Question: {_content_to_text(messages[-1].content) if messages else ""}

Reasoning Steps:
{chr(10).join(f"- {step}" for step in reasoning_steps)}

Tool Results:
{json.dumps(tool_results, indent=2)[:2000]}
"""

        system_prompt = """You are an expert MBSE assistant. Based on the information gathered, 
provide a clear, comprehensive answer to the user's question. Include specific details from the data."""

        response_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context),
        ]

        response = self.llm.invoke(response_messages)

        state["messages"].append(AIMessage(content=_content_to_text(response.content)))

        logger.info("Generated final response")

        return state

    def run(self, user_message: str) -> str:
        """Run the agent on a user message using the React agent"""
        try:
            # Use the prebuilt React agent
            result = self.graph.invoke(
                {"messages": [HumanMessage(content=user_message)]}
            )

            # Extract the final response
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                if hasattr(last_message, "content"):
                    return last_message.content
                return str(last_message)

            return "I apologize, but I couldn't generate a response."
        except Exception as e:  # noqa: BLE001 pylint: disable=broad-exception-caught
            logger.error(f"Agent execution failed: {e}")
            return f"An error occurred: {str(e)}"


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Initialize agent (requires OpenAI API key)
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        exit(1)

    agent = MBSEAgent(api_key=openai_api_key)

    # Example queries
    queries = [
        "How many classes are in the system?",
        "Show me the traceability from requirements to design elements",
        "What would be impacted if I change the Sensor class?",
        "Extract all parameters from the Control System class",
    ]

    print("=" * 60)
    print("MBSE AI Agent - LangGraph Framework")
    print("=" * 60)

    for i, example_query in enumerate(queries, 1):
        print(f"\n\n[Query {i}]: {example_query}")
        print("-" * 60)
        agent_response = agent.run(example_query)
        print(f"\n[Response]: {agent_response}")
