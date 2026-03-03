"""
PLM Specialized Agent
Wraps PLM Connectors (Teamcenter, Windchill, SAP) and the PLMXML ingest service
to provide unified tool access for the Orchestrator.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger

from src.integrations.base_connector import PLMConfig, PLMSystem
from src.integrations.teamcenter_connector import TeamcenterConnector
from src.integrations.windchill_connector import WindchillConnector
from src.integrations.sap_odata_connector import SAPODataConnector
from src.web.services.plmxml_ingest_service import PLMXMLIngestConfig, PLMXMLIngestService
from src.web.services import get_neo4j_service


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

    # -----------------------------------------------------------------------
    # PLMXML serialization (offline / file-based)
    # -----------------------------------------------------------------------

    def ingest_plmxml(self, file_path: str, label: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse a Teamcenter PLMXML export file and serialize the full object model
        (Items, Revisions, BOM lines, DataSets) into the Neo4j knowledge graph.

        Args:
            file_path: Absolute or repo-relative path to the .xml / .plmxml file
            label:     Optional display name override

        Returns:
            Ingest statistics dict
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"PLMXML file not found: {p}")
        cfg = PLMXMLIngestConfig(create_step_links=True)
        svc = PLMXMLIngestService(cfg)
        result = svc.ingest_file(p, file_label=label)
        logger.info(f"PLMAgent.ingest_plmxml: {p.name} -> items={result.items_upserted}, revs={result.revisions_upserted}")
        return result.__dict__

    def list_plmxml_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return :PLMXMLItem nodes already in the graph."""
        neo4j = get_neo4j_service()
        with neo4j.driver.session(database=neo4j.database) as session:
            rows = session.run(
                "MATCH (n:PLMXMLItem) "
                "RETURN n.item_id AS item_id, n.name AS name, n.item_type AS item_type "
                "ORDER BY n.item_id LIMIT $limit",
                limit=limit,
            )
            return [dict(r) for r in rows]

    def get_plmxml_bom(self, item_id: str) -> List[Dict[str, Any]]:
        """Return flattened BOM for a TC item number."""
        neo4j = get_neo4j_service()
        cypher = """
        MATCH (root:PLMXMLItem {item_id: $item_id})
        OPTIONAL MATCH (root)-[:HAS_REVISION]->(:PLMXMLRevision)
                       -[:HAS_BOM_LINE]->(b:PLMXMLBOMLine)
                       -[:REFERENCES]->(child:PLMXMLItem)
        RETURN root.item_id AS root_id, b.quantity AS qty,
               b.find_num AS find_num, child.item_id AS child_id,
               child.name AS child_name, child.item_type AS child_type
        LIMIT 500
        """
        with neo4j.driver.session(database=neo4j.database) as session:
            rows = session.run(cypher, item_id=item_id)
            return [dict(r) for r in rows]

    def summarize(self, query: str) -> str:
        """
        Respond to a natural-language query about PLMXML / PLM data in the graph.
        Called from plm_agent_node when task_type == 'plm_ingest' or 'plm_query'.
        """
        q = query.lower()

        # Ingest request
        import re as _re
        path_match = _re.search(
            r"(?:ingest|load|import)\s+['\"]?([^'\" ]+\.(?:xml|plmxml|plmxml[56]))['\"]?",
            query,
            _re.IGNORECASE,
        )
        if path_match:
            try:
                stats = self.ingest_plmxml(path_match.group(1))
                lines = "\n".join(f"- **{k}**: {v}" for k, v in stats.items() if not k.startswith("__"))
                return f"PLMXML ingestion complete:\n\n{lines}"
            except FileNotFoundError as exc:
                return (
                    f"File not found: `{exc}`\n\n"
                    "Provide an absolute path or use `POST /api/plmxml/ingest`."
                )

        # BOM query
        bom_match = _re.search(r"bom\s+(?:for\s+|of\s+)?([A-Z0-9_-]+)", query, _re.IGNORECASE)
        if bom_match or any(k in q for k in ("bom", "bill of material")):
            item_id = bom_match.group(1) if bom_match else None
            if item_id:
                rows = self.get_plmxml_bom(item_id)
                if rows:
                    lines = "\n".join(
                        f"- {r.get('find_num','?')} | **{r.get('child_id','?')}** {r.get('child_name','?')} × {r.get('qty',1)}"
                        for r in rows
                    )
                    return f"### BOM for {item_id}\n\n{lines}"
                return f"No BOM data found in graph for item `{item_id}`. Ingest a PLMXML file first."

        # List items
        if any(k in q for k in ("list", "show", "item", "part", "assembly")):
            rows = self.list_plmxml_items(limit=30)
            if rows:
                lines = "\n".join(
                    f"- **{r.get('item_id','?')}** — {r.get('name','?')} ({r.get('item_type','?')})"
                    for r in rows
                )
                return f"### PLM Items in graph ({len(rows)} shown)\n\n{lines}"
            return (
                "No :PLMXMLItem nodes found in the graph yet.\n\n"
                "Ingest a Teamcenter PLMXML export with:\n"
                "`POST /api/plmxml/ingest  {\"path\": \"path/to/export.xml\"}`"
            )

        return (
            "PLM Agent is ready. Available actions:\n"
            "- **Ingest PLMXML**: `ingest path/to/export.xml`\n"
            "- **BOM query**: `show BOM for <item-id>`\n"
            "- **List parts**: `list PLM items`\n"
            "- **REST**: `POST /api/plmxml/ingest`, `GET /api/plmxml/bom/{item_id}`"
        )
