"""
OSLC TRS Service (Tracked Resource Set)
Handles the "Smart Linking" notification mechanism.
Maintains a ChangeLog of resource modifications so external tools can stay in sync.
"""

import time
from typing import Dict, List, Optional
from loguru import logger
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import DCTERMS, XSD
from src.web.services import get_neo4j_service
from src.web.services.redis_service import get_redis_service, is_redis_enabled
from src.web.utils.runtime_config import get_public_base_url

# Namespaces
OSLC = Namespace("http://open-services.net/ns/core#")
TRS = Namespace("http://open-services.net/ns/core/trs#")

class OSLCTRSService:
    def __init__(self, base_url: str | None = None):
        resolved = base_url or get_public_base_url()
        self.base_url = resolved.rstrip("/")
        self.neo4j = get_neo4j_service()
        self.redis_enabled = is_redis_enabled()

    async def get_tracked_resource_set(self) -> Graph:
        """
        Generate the main TRS descriptor.
        Points to the Base (Initial Load) and ChangeLog (Incremental Updates).
        """
        g = Graph()
        g.bind("trs", TRS)
        g.bind("dcterms", DCTERMS)

        trs_uri = URIRef(f"{self.base_url}/oslc/trs")
        base_uri = URIRef(f"{self.base_url}/oslc/trs/base")
        changelog_uri = URIRef(f"{self.base_url}/oslc/trs/changelog")

        g.add((trs_uri, RDF.type, TRS.TrackedResourceSet))
        g.add((trs_uri, DCTERMS.title, Literal("MBSE Graph Tracked Resource Set")))
        g.add((trs_uri, TRS.base, base_uri))
        g.add((trs_uri, TRS.changeLog, changelog_uri))

        return g

    async def get_base_page(self, page: int = 1) -> Graph:
        """
        Generate a page of the Base (All Resources).
        Queries Neo4j for all Requirements, Parts, etc.
        """
        g = Graph()
        g.bind("trs", TRS)
        g.bind("oslc", OSLC)

        base_uri = URIRef(f"{self.base_url}/oslc/trs/base")
        page_uri = URIRef(f"{self.base_url}/oslc/trs/base?page={page}")
        
        g.add((base_uri, RDF.type, TRS.Base))
        g.add((base_uri, TRS.cutoffEvent, URIRef("urn:event:now"))) # Placeholder
        
        # Paging Logic (Simplified for demo)
        limit = 50
        skip = (page - 1) * limit
        
        # Fetch Neo4j Nodes (Requirements & Parts)
        query = """
        MATCH (n) WHERE 'Requirement' IN labels(n) OR 'Part' IN labels(n)
        RETURN n.id as id, labels(n) as labels
        SKIP $skip LIMIT $limit
        """
        results = self.neo4j.execute_query(query, {"skip": skip, "limit": limit})
        
        # Add members to graph
        for record in results:
            # Determine Resource Type mapping
            label = record['labels'][0] if record['labels'] else "Resource"
            path_segment = "requirements" if label == "Requirement" else "parts"
            
            res_uri = URIRef(f"{self.base_url}/oslc/rm/{path_segment}/{record['id']}")
            g.add((base_uri, TRS.member, res_uri))

        # Next Page Link (if results full)
        if len(results) == limit:
            next_page = URIRef(f"{self.base_url}/oslc/trs/base?page={page+1}")
            g.add((page_uri, OSLC.nextPage, next_page))

        return g

    async def get_changelog(self) -> Graph:
        """
        Generate the Change Log (Recent Events).
        Reads from Redis List (if enabled) or mocked in-memory list.
        """
        g = Graph()
        g.bind("trs", TRS)
        
        cl_uri = URIRef(f"{self.base_url}/oslc/trs/changelog")
        g.add((cl_uri, RDF.type, TRS.ChangeLog))
        
        events = []
        if self.redis_enabled:
            redis = await get_redis_service()
            # Fetch last 20 events
            events_data = await redis.client.lrange("oslc:changelog", 0, 19)
            if events_data:
                import json as _json
                events = [_json.loads(e) for e in events_data]
        
        # Process Events
        for event in events:
            evt_uri = URIRef(event.get('uri', f"urn:event:{int(time.time())}"))
            res_uri = URIRef(event.get('resource'))
            evt_type =  TRS.Creation if event['type'] == 'create' else \
                        TRS.Modification if event['type'] == 'update' else TRS.Deletion
            
            g.add((cl_uri, TRS.change, evt_uri))
            g.add((evt_uri, RDF.type, evt_type))
            g.add((evt_uri, TRS.changed, res_uri))
            g.add((evt_uri, TRS.order, Literal(event['order'], datatype=XSD.integer)))

        return g

    async def publish_event(self, resource_uri: str, event_type: str = "update"):
        """
        Publish a change event to the ChangeLog.
        Args:
            resource_uri: The URI of the changed resource.
            event_type: 'create', 'update', or 'delete'.
        """
        if not self.redis_enabled:
            logger.warning("Redis disabled; cannot publish TRS event.")
            return

        event = {
            "uri": f"urn:event:{int(time.time() * 1000)}",
            "resource": resource_uri,
            "type": event_type,
            "timestamp": time.time(),
            "order": int(time.time() * 1000)
        }
        
        try:
            redis = await get_redis_service()
            # Push to head of list, trim to keep history manageable (e.g., 1000 events)
            import json as _json
            await redis.client.lpush("oslc:changelog", _json.dumps(event))
            await redis.client.ltrim("oslc:changelog", 0, 999)
            logger.info(f"Published TRS Event: {event_type} on {resource_uri}")
        except Exception as e:
            logger.error(f"Failed to publish TRS event: {e}")

    async def append_change_event(
        self, resource_uri: str, change_type: str = "create"
    ) -> None:
        """Convenience wrapper around ``publish_event``.

        Accepts ``change_type`` as 'create', 'update', or 'delete'.
        Non-blocking: errors are logged but never raised.
        """
        try:
            await self.publish_event(resource_uri, event_type=change_type)
        except Exception as exc:
            logger.warning(f"TRS append_change_event failed (non-blocking): {exc}")
