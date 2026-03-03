"""
Simulation Specialized Agent
Handles interaction with simulation tools and manages simulation data in the graph.
Implements MoSSEC (ISO 10303-243) Activity/Context model.
"""

import asyncio
import json
import time
from uuid import uuid4
from typing import Dict, List, Any, Optional
from loguru import logger
from src.agents.langgraph_agent import MBSETools
from src.web.services import get_neo4j_service
from src.web.services.oslc_trs_service import OSLCTRSService

class SimulationAgent:
    """
    Agent responsible for simulation workflows:
    1. Extracting parameters from MBSE models
    2. Validating parameters against constraints
    3. Triggering external simulations (Mocked)
    4. Storing results back to the graph as MoSSEC Activities
    """

    def __init__(self):
        self.tools = MBSETools()
        self.neo4j = get_neo4j_service()
        self.trs = OSLCTRSService()

    async def _create_mossec_activity(self, study_id: Optional[str], activity_type: str, agent_id: str = "SimulationAgent") -> str:
        """
        Creates a MoSSEC Activity node representing this agent's execution.
        Links to a Study if provided.
        Returns the Activity UID.
        """
        activity_uid = f"act-{uuid4()}"
        query = """
        MERGE (a:Agent {name: $agent_id})
        CREATE (act:MoSSEC_Activity:Activity {
            uid: $uid,
            name: $type + ' Run ' + toString(datetime()),
            type: $type,
            status: 'Running',
            started_at: datetime()
        })
        MERGE (act)-[:WAS_ASSOCIATED_WITH]->(a)
        RETURN act
        """
        self.neo4j.execute_query(query, {"uid": activity_uid, "type": activity_type, "agent_id": agent_id})
        
        # Link to Study if exists
        if study_id:
            link_query = """
            MATCH (s:MoSSEC_Study {uid: $study_id})
            MATCH (act:MoSSEC_Activity {uid: $act_uid})
            MERGE (act)-[:PART_OF]->(s)
            """
            self.neo4j.execute_query(link_query, {"study_id": study_id, "act_uid": activity_uid})

        # OSLC TRS Notification
        try:
            await self.trs.publish_event(f"urn:mossec:activity:{activity_uid}", "create")
        except Exception as e:
            logger.warning(f"TRS Publish failed: {e}")

        return activity_uid

    async def _complete_mossec_activity(self, activity_uid: str, status: str, results: Dict[str, Any]):
        """
        Updates the Activity status and links results.
        """
        query = """
        MATCH (act:MoSSEC_Activity {uid: $uid})
        SET act.status = $status,
            act.ended_at = datetime(),
            act.results_summary = $summary
        RETURN act
        """
        self.neo4j.execute_query(query, {"uid": activity_uid, "status": status, "summary": json.dumps(results)})

        # Create Result Node
        result_uid = f"res-{uuid4()}"
        res_query = """
        MATCH (act:MoSSEC_Activity {uid: $act_uid})
        CREATE (res:MoSSEC_Result:AnalysisResult {
            uid: $res_uid,
            name: 'Result for ' + act.name,
            data: $data,
            created_at: datetime()
        })
        MERGE (res)-[:GENERATED_BY]->(act)
        """
        self.neo4j.execute_query(res_query, {"act_uid": activity_uid, "res_uid": result_uid, "data": json.dumps(results)})

        # OSLC TRS Notification
        try:
            await self.trs.publish_event(f"urn:mossec:activity:{activity_uid}", "update")
            await self.trs.publish_event(f"urn:mossec:result:{result_uid}", "create")
        except Exception as e:
            logger.warning(f"TRS Publish failed: {e}")

    def get_simulation_parameters(self, model_id: str) -> Dict[str, Any]:
        """Extract simulation parameters for a given model from the knowledge graph."""
        logger.info(f"Simulation Agent: Extracting parameters for {model_id}")
        try:
            query = """
            MATCH (owner)-[:HAS_ATTRIBUTE]->(p:Property)
            WHERE owner.id = $model_id
               OR owner.uid = $model_id
               OR owner.name = $model_id
            OPTIONAL MATCH (p)-[:TYPED_BY]->(t)
            RETURN p.name AS name,
                   p.default AS value,
                   t.name AS unit
            ORDER BY p.name
            """
            rows = self.neo4j.execute_query(query, {"model_id": model_id})
            parameters = [
                {
                    "name": r["name"],
                    "value": r.get("value"),
                    "unit": r.get("unit"),
                }
                for r in rows
                if r.get("name")
            ]
            return {"model_id": model_id, "parameters": parameters}
        except Exception as e:
            return {"error": str(e)}

    async def run_simulation(self, simulation_type: str, parameters: Dict[str, Any], study_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a simulation with MoSSEC compliance.
        1. Create Activity (Started)
        2. Run logic (Mock)
        3. Create Result, Link, Complete Activity
        """
        logger.info(f"Simulation Agent: Running {simulation_type} simulation...")
        
        # 1. MoSSEC: Create Activity
        activity_uid = await self._create_mossec_activity(study_id, "SimulationRun")

        # 2. Execution — delegate to external runner when available.
        # Currently creates the Activity graph structure and records
        # whatever result the caller provides or runs a no-op stub.
        await asyncio.sleep(0.1)  # yield control briefly

        result: Dict[str, Any] = {}
        if simulation_type.lower() in ("fea", "cfd", "thermal", "modal"):
            # Placeholder result — replace with real solver integration.
            result = {
                "status": "Stub",
                "simulation_type": simulation_type,
                "message": (
                    f"No external {simulation_type.upper()} solver is configured. "
                    "Activity was recorded in the graph; attach real results via "
                    "the /simulation/results endpoint."
                ),
            }
        else:
            result = {"status": "Error", "error": f"Unknown simulation type: {simulation_type}"}

        # 3. MoSSEC: Complete Activity & Link Results
        act_status = "Completed" if result.get("status") != "Error" else "Failed"
        await self._complete_mossec_activity(activity_uid, act_status, result)
        
        return result

    def validate_results(self, results: Dict[str, Any], requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare simulation results against requirements.

        Each requirement dict should contain at least:
            - name: str  (matched against result keys)
            - operator: str  ("<=", ">=", "==", "<", ">")
            - threshold: float
        """
        logger.info("Simulation Agent: Validating results against requirements")
        violations: List[Dict[str, Any]] = []

        _OPS = {
            "<=": lambda a, b: a <= b,
            ">=": lambda a, b: a >= b,
            "==": lambda a, b: a == b,
            "<": lambda a, b: a < b,
            ">": lambda a, b: a > b,
        }

        for req in requirements:
            name = req.get("name", "")
            op_str = req.get("operator", "<=")
            threshold = req.get("threshold")
            actual = results.get(name)

            if actual is None or threshold is None:
                continue

            try:
                op_fn = _OPS.get(op_str)
                if op_fn is None:
                    violations.append({"name": name, "reason": f"Unknown operator '{op_str}'"})
                    continue
                if not op_fn(float(actual), float(threshold)):
                    violations.append({
                        "name": name,
                        "actual": actual,
                        "operator": op_str,
                        "threshold": threshold,
                    })
            except (TypeError, ValueError):
                violations.append({"name": name, "reason": "Non-numeric comparison failed"})

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "checked": len(requirements),
        }
