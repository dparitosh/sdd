"""
PLM Specialized Agent
Wraps PLM Connectors (Teamcenter, Windchill, SAP) to provide unified tool access for the Orchestrator.
"""

import os
from typing import Dict, List, Optional, Any
from loguru import logger

from src.integrations.base_connector import PLMConfig, PLMSystem
from src.integrations.teamcenter_connector import TeamcenterConnector
from src.integrations.windchill_connector import WindchillConnector
from src.integrations.sap_odata_connector import SAPODataConnector


class PLMAgent:
    """
    Specialized Agent for PLM interactions.
    Handles connection management and provides unified methods for the orchestrator.
    """

    def __init__(self, system_type: str = "teamcenter"):
        self.system = system_type.lower()
        self.connector = self._initialize_connector()

    def _initialize_connector(self):
        """Initialize the appropriate PLM connector based on configuration"""
        
        # Load config from env
        base_url = os.getenv(f"{self.system.upper()}_URL", "http://localhost:8080")
        username = os.getenv(f"{self.system.upper()}_USER", "admin")
        password = os.getenv(f"{self.system.upper()}_PASSWORD", "password")

        config = PLMConfig(
            system_type=PLMSystem(self.system) if self.system in [e.value for e in PLMSystem] else PLMSystem.TEAMCENTER,
            base_url=base_url,
            username=username,
            password=password
        )

        if self.system == "teamcenter":
            return TeamcenterConnector(config)
        elif self.system == "windchill":
            return WindchillConnector(config)
        elif self.system == "sap_plm" or self.system == "sap":
            return SAPODataConnector(config)
        else:
            logger.warning(f"Unknown PLM system {self.system}, defaulting to Teamcenter")
            return TeamcenterConnector(config)

    async def check_part_availability(self, part_ids: List[str]) -> Dict[str, Any]:
        """Check status/availability of parts in PLM"""
        logger.info(f"PLM Agent ({self.system}): Checking parts {part_ids}")
        results = {}
        
        if not self.connector:
            return {"error": "Connector not initialized"}

        try:
            # Ensure authenticated
            if not self.connector.is_authenticated:
                await self.connector.authenticate()

            for part_id in part_ids:
                # Use get_part_details from connector
                details = await self.connector.get_part_details(part_id)
                if details:
                    results[part_id] = {
                        "status": details.get("status", "Unknown"),
                        "revision": details.get("revision", "A"),
                        "name": details.get("name")
                    }
                else:
                    results[part_id] = "Not Found"
            
            return results
        except Exception as e:
            logger.error(f"PLM Agent Error: {e}")
            return {"error": str(e)}

    async def get_bom(self, assembly_id: str) -> Dict[str, Any]:
        """Retrieve Bill of Materials"""
        logger.info(f"PLM Agent ({self.system}): Getting BOM for {assembly_id}")
        
        try:
            if not self.connector.is_authenticated:
                await self.connector.authenticate()
                
            bom = await self.connector.get_bom(assembly_id)
            return {"assembly_id": assembly_id, "bom": bom}
        except Exception as e:
            logger.error(f"PLM Agent Error: {e}")
            return {"error": str(e)}

    async def calculate_impact(self, change_id: str) -> Dict[str, Any]:
        """Calculate change impact (Mock/Wrapper)"""
        # This would typically call a dedicated PLM endpoint or use graph analysis
        logger.info(f"PLM Agent: Calculating impact for change {change_id}")
        return {
            "change_id": change_id,
            "impact_score": "High",
            "affected_assemblies": ["ASM-001", "ASM-002"]
        }
