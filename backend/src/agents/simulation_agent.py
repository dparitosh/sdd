"""
Simulation Specialized Agent
Handles interaction with simulation tools and manages simulation data in the graph.
Implements MoSSEC (ISO 10303-243) Activity/Context model.
"""

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
        """Extract simulation parameters for a given model"""
        logger.info(f"Simulation Agent: Extracting parameters for {model_id}")
        # real implementation would use self.tools to query the parameters endpoint
        try:
            # Using MBSETools generic search or specialized endpoint if available
            # For now, we simulate a parameter extraction
            return {
                "model_id": model_id,
                "parameters": [
                    {"name": "Mass", "value": 150.5, "unit": "kg"},
                    {"name": "ElasticModulus", "value": 210, "unit": "GPa"},
                    {"name": "MaxLoad", "value": 5000, "unit": "N"}
                ]
            }
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

        # 2. Execution (Mock)
        # Simulate delay
        time.sleep(1) 
        
        result = {}
        if simulation_type.lower() == "fea":
            result = {
                "status": "Success",
                "max_stress": "150 MPa",
                "safety_factor": 1.5,
                "passed": True
            }
        elif simulation_type.lower() == "cfd":
            result = {
                "status": "Success",
                "drag_coefficient": 0.32,
                "passed": True
            }
        else:
            result = {"error": "Unknown simulation type"}

        # 3. MoSSEC: Complete Activity & Link Results
        status = "Completed" if "error" not in result else "Failed"
        await self._complete_mossec_activity(activity_uid, status, result)
        
        return result

    def validate_results(self, results: Dict[str, Any], requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare simulation results against requirements"""
        logger.info("Simulation Agent: Validating results against requirements")
        validation = {
            "compliant": True,
            "violations": []
        }
        
        # Simple logic for demo
        for req in requirements:
            # Mock check
            pass
            
        return validation
