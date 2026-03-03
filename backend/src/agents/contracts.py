"""Agent contracts & registry.

Defines a base ``AgentContract`` dataclass that every agent should conform to,
and a global ``AGENT_REGISTRY`` mapping agent names to their contracts.

This enables the orchestrator to introspect agent capabilities, validate
inputs/outputs, and route tasks based on ``task_types``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Type


# ---------------------------------------------------------------------------
# Base contract
# ---------------------------------------------------------------------------

@dataclass
class AgentContract:
    """Describes an agent's interface contract."""

    name: str
    description: str
    task_types: List[str]
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    agent_class: str = ""  # dotted import path


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

AGENT_REGISTRY: Dict[str, AgentContract] = {
    "mbse": AgentContract(
        name="MBSEAgent",
        description="Knowledge-graph queries (Neo4j): traceability, impact analysis, BOM sync.",
        task_types=["traceability", "impact_analysis", "requirement_check", "bom_sync", "kg_query", "kg_expand"],
        input_schema={
            "query": {"type": "string", "required": True},
            "task_type": {"type": "string", "required": True},
        },
        output_schema={
            "status": {"type": "string"},
            "data": {"type": "object"},
            "error": {"type": "string", "nullable": True},
        },
        agent_class="src.agents.langgraph_agent.MBSEAgent",
    ),
    "plm": AgentContract(
        name="PLMAgent",
        description="PLM system integration (Teamcenter/Windchill bridge).",
        task_types=["plm_ingest", "plm_query", "plm_sync"],
        input_schema={
            "query": {"type": "string", "required": True},
            "task_type": {"type": "string", "required": True},
        },
        output_schema={
            "status": {"type": "string"},
            "data": {"type": "object"},
        },
        agent_class="src.agents.plm_agent.PLMAgent",
    ),
    "simulation": AgentContract(
        name="SimulationAgent",
        description="Simulation parameter retrieval, execution stubs, and result validation.",
        task_types=["simulation_params", "simulation_run", "simulation_validate"],
        input_schema={
            "query": {"type": "string", "required": True},
        },
        output_schema={
            "status": {"type": "string"},
            "data": {"type": "object"},
        },
        agent_class="src.agents.simulation_agent.SimulationAgent",
    ),
    "ontology": AgentContract(
        name="OntologyAgent",
        description="OWL ontology operations: classification chain, class hierarchy.",
        task_types=["ont_classify", "ont_hierarchy", "ont_search"],
        input_schema={
            "query": {"type": "string", "required": True},
        },
        output_schema={
            "status": {"type": "string"},
            "data": {"type": "object"},
        },
        agent_class="src.agents.ontology_agent.OntologyAgent",
    ),
    "step": AgentContract(
        name="StepAgent",
        description="STEP file ingestion and AP242 geometry extraction.",
        task_types=["step_ingest", "step_query"],
        input_schema={
            "file_path": {"type": "string", "required": True},
        },
        output_schema={
            "status": {"type": "string"},
            "data": {"type": "object"},
        },
        agent_class="src.agents.step_agent.StepAgent",
    ),
    "semantic": AgentContract(
        name="SemanticAgent",
        description="RAG pipeline: semantic vector search + LLM synthesis.",
        task_types=["semantic_search", "semantic_insight"],
        input_schema={
            "query": {"type": "string", "required": True},
            "top_k": {"type": "integer", "default": 10},
        },
        output_schema={
            "status": {"type": "string"},
            "data": {
                "hits": {"type": "array"},
                "expanded": {"type": "object"},
            },
        },
        agent_class="src.agents.semantic_agent.SemanticAgent",
    ),
    "shacl": AgentContract(
        name="SHACLAgent",
        description="SHACL validation of graph nodes against shape definitions.",
        task_types=["shacl_validate", "shacl_report"],
        input_schema={
            "label": {"type": "string", "description": "Neo4j node label to validate"},
        },
        output_schema={
            "status": {"type": "string"},
            "violations": {"type": "array"},
        },
        agent_class="src.web.services.shacl_validation_service.SHACLValidationService",
    ),
    "export": AgentContract(
        name="ExportAgent",
        description="Data export in multiple formats (RDF, CSV, JSON).",
        task_types=["export_rdf", "export_csv", "export_json"],
        input_schema={
            "format": {"type": "string", "required": True},
            "node_types": {"type": "array"},
        },
        output_schema={
            "status": {"type": "string"},
            "file_path": {"type": "string"},
        },
        agent_class="src.web.routes.export_fastapi",
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_contract(agent_name: str) -> AgentContract | None:
    """Look up an agent contract by name."""
    return AGENT_REGISTRY.get(agent_name)


def get_contract_for_task(task_type: str) -> AgentContract | None:
    """Find the first agent contract that handles *task_type*."""
    for contract in AGENT_REGISTRY.values():
        if task_type in contract.task_types:
            return contract
    return None


def list_all_task_types() -> List[str]:
    """Return a flat list of all supported task types."""
    types: List[str] = []
    for contract in AGENT_REGISTRY.values():
        types.extend(contract.task_types)
    return sorted(set(types))
