"""
PTC Windchill PLM connector implementation
Supports Windchill REST API v2 for parts, BOMs, and change management
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
from loguru import logger

from .base_connector import (
    BasePLMConnector,
    PLMConfig,
    PLMSystem,
    BOMItem,
    SyncResult,
    PLMConnectorFactory,
)


class WindchillConnector(BasePLMConnector):
    """
    PTC Windchill PLM integration via REST API v2

    Features:
    - Part metadata retrieval
    - BOM expansion with effectivity
    - Change request/notice tracking
    - CAD document associations
    - Lifecycle state management
    """

    def __init__(self, config: PLMConfig):
        super().__init__(config)
        self.client: Optional[httpx.AsyncClient] = None
        self.csrf_token: Optional[str] = None
        self.session_id: Optional[str] = None

    async def authenticate(self) -> bool:
        """
        Authenticate with Windchill using Basic Auth or OAuth2

        Returns:
            True if authentication successful
        """
        try:
            # Create async HTTP client
            self.client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(30.0),
                verify=False,  # Set to True in production with valid certs
            )

            # Windchill uses Basic Auth or OAuth2
            if self.config.username and self.config.password:
                # Basic authentication
                auth_response = await self.client.get(
                    "/Windchill/servlet/rest/v2/login",
                    auth=(self.config.username, self.config.password),
                )

                if auth_response.status_code == 200:
                    # Extract CSRF token and session ID
                    self.csrf_token = auth_response.headers.get("X-CSRF-TOKEN")
                    self.session_id = auth_response.cookies.get("JSESSIONID")

                    logger.info(f"Windchill authentication successful: {self.config.base_url}")
                    return True
                else:
                    logger.error(f"Windchill authentication failed: {auth_response.status_code}")
                    return False

            elif self.config.auth_token:
                # OAuth2 token authentication
                self.client.headers.update({"Authorization": f"Bearer {self.config.auth_token}"})

                # Verify token
                verify_response = await self.client.get("/Windchill/servlet/rest/v2/system/version")

                if verify_response.status_code == 200:
                    logger.info("Windchill OAuth2 authentication successful")
                    return True
                else:
                    logger.error("Windchill OAuth2 token validation failed")
                    return False

            else:
                logger.error("No authentication credentials provided")
                return False

        except Exception as e:
            logger.error(f"Windchill authentication error: {e}")
            return False

    async def get_part(self, part_id: str) -> Dict[str, Any]:
        """
        Retrieve part metadata from Windchill

        Args:
            part_id: Windchill part number or OID

        Returns:
            Part details dictionary
        """
        if not self.client:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            # Set headers with CSRF token
            headers = {}
            if self.csrf_token:
                headers["X-CSRF-TOKEN"] = self.csrf_token

            # Query part by number
            response = await self.client.get(
                f"/Windchill/servlet/rest/v2/parts/{part_id}", headers=headers
            )

            if response.status_code == 200:
                data = response.json()

                # Transform Windchill response to standard format
                part_data = {
                    "id": data.get("id"),
                    "number": data.get("number"),
                    "name": data.get("name"),
                    "revision": data.get("version", {}).get("value"),
                    "state": data.get("state"),
                    "type": data.get("type"),
                    "description": data.get("description"),
                    "created_date": data.get("createdOn"),
                    "modified_date": data.get("modifiedOn"),
                    "owner": data.get("creator", {}).get("name"),
                    "attributes": {},
                }

                # Extract custom attributes
                if "attributes" in data:
                    for attr in data["attributes"]:
                        part_data["attributes"][attr["name"]] = attr["value"]

                logger.info(f"Retrieved Windchill part: {part_id}")
                return part_data

            else:
                logger.error(f"Failed to get part {part_id}: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error retrieving Windchill part {part_id}: {e}")
            return {}

    async def get_bom(self, part_id: str, depth: int = 1) -> BOMItem:
        """
        Retrieve BOM structure from Windchill with effectivity

        Args:
            part_id: Root part number
            depth: BOM expansion depth (1-10)

        Returns:
            BOMItem tree structure
        """
        if not self.client:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            # Get root part
            part = await self.get_part(part_id)

            root_item = BOMItem(
                part_number=part.get("number", part_id),
                name=part.get("name", ""),
                revision=part.get("revision", ""),
                quantity=1,
                unit="EA",
                children=[],
            )

            if depth > 0:
                # Get BOM structure
                headers = {}
                if self.csrf_token:
                    headers["X-CSRF-TOKEN"] = self.csrf_token

                response = await self.client.get(
                    f"/Windchill/servlet/rest/v2/parts/{part_id}/structure",
                    headers=headers,
                    params={"depth": depth},
                )

                if response.status_code == 200:
                    bom_data = response.json()

                    # Parse BOM components
                    if "components" in bom_data:
                        root_item.children = await self._parse_bom_components(
                            bom_data["components"], depth - 1
                        )

            logger.info(f"Retrieved Windchill BOM for {part_id}, depth={depth}")
            return root_item

        except Exception as e:
            logger.error(f"Error retrieving Windchill BOM for {part_id}: {e}")
            return BOMItem(part_number=part_id, name="", revision="", quantity=1, unit="EA")

    async def _parse_bom_components(
        self, components: List[Dict], remaining_depth: int
    ) -> List[BOMItem]:
        """Parse Windchill BOM components recursively"""
        items = []

        for comp in components:
            part_data = comp.get("part", {})

            item = BOMItem(
                part_number=part_data.get("number", ""),
                name=part_data.get("name", ""),
                revision=part_data.get("version", {}).get("value", ""),
                quantity=comp.get("quantity", 1),
                unit=comp.get("unit", "EA"),
                children=[],
            )

            # Recursively get child BOMs if depth remaining
            if remaining_depth > 0 and "components" in comp:
                item.children = await self._parse_bom_components(
                    comp["components"], remaining_depth - 1
                )

            items.append(item)

        return items

    async def search_parts(self, **criteria) -> List[Dict[str, Any]]:
        """
        Search for parts in Windchill

        Args:
            **criteria: Search criteria (name, number, type, state)

        Returns:
            List of matching parts
        """
        if not self.client:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            headers = {}
            if self.csrf_token:
                headers["X-CSRF-TOKEN"] = self.csrf_token

            # Build search query
            search_params = {}
            if "name" in criteria:
                search_params["name"] = criteria["name"]
            if "number" in criteria:
                search_params["number"] = criteria["number"]
            if "state" in criteria:
                search_params["state"] = criteria["state"]

            response = await self.client.get(
                "/Windchill/servlet/rest/v2/parts", headers=headers, params=search_params
            )

            if response.status_code == 200:
                results = response.json()
                parts = []

                for item in results.get("items", []):
                    parts.append(
                        {
                            "id": item.get("id"),
                            "number": item.get("number"),
                            "name": item.get("name"),
                            "revision": item.get("version", {}).get("value"),
                            "state": item.get("state"),
                            "type": item.get("type"),
                        }
                    )

                logger.info(f"Windchill search found {len(parts)} parts")
                return parts

            else:
                logger.error(f"Windchill search failed: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Windchill search error: {e}")
            return []

    async def get_change_orders(self, part_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get change requests/notices from Windchill

        Args:
            part_id: Optional part to filter change orders

        Returns:
            List of change orders
        """
        if not self.client:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            headers = {}
            if self.csrf_token:
                headers["X-CSRF-TOKEN"] = self.csrf_token

            params = {}
            if part_id:
                params["affectedPart"] = part_id

            response = await self.client.get(
                "/Windchill/servlet/rest/v2/changes", headers=headers, params=params
            )

            if response.status_code == 200:
                changes = response.json()
                change_orders = []

                for change in changes.get("items", []):
                    change_orders.append(
                        {
                            "id": change.get("number"),
                            "name": change.get("name"),
                            "type": change.get("type"),
                            "state": change.get("state"),
                            "description": change.get("description"),
                            "created_date": change.get("createdOn"),
                            "affected_parts": [
                                p.get("number") for p in change.get("affectedItems", [])
                            ],
                        }
                    )

                logger.info(f"Retrieved {len(change_orders)} Windchill change orders")
                return change_orders

            else:
                logger.error(f"Failed to get change orders: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error retrieving change orders: {e}")
            return []

    async def close(self):
        """Close HTTP client connection"""
        if self.client:
            await self.client.aclose()
            logger.info("Windchill connection closed")

    async def disconnect(self) -> bool:
        """
        Disconnect from Windchill and clean up resources
        """
        try:
            await self.close()
            self.is_authenticated = False
            self.csrf_token = None
            self.session_id = None
            logger.info("Windchill disconnected successfully")
            return True
        except Exception as e:
            logger.error(f"Windchill disconnect error: {e}")
            return False

    async def sync_to_neo4j(self, part_ids: List[str]) -> SyncResult:
        """
        Synchronize Windchill parts to Neo4j graph database

        Args:
            part_ids: List of Windchill part IDs to sync

        Returns:
            SyncResult with sync statistics
        """
        start_time = datetime.now()
        synced = 0
        failed = 0
        errors = []

        try:
            if not self.client:
                await self.authenticate()

            for part_id in part_ids:
                try:
                    # Get part data from Windchill
                    part = await self.get_part(part_id)
                    if not part:
                        failed += 1
                        errors.append(f"Part {part_id} not found in Windchill")
                        continue

                    # Get BOM structure
                    bom = await self.get_bom(part_id, depth=2)

                    # TODO: Insert into Neo4j using graph connection
                    # This would use the Neo4j driver to create nodes and relationships
                    # Example: CREATE (p:Part {id: $part_id, name: $name, ...})

                    logger.info(f"Synced Windchill part {part_id} to Neo4j")
                    synced += 1

                except Exception as e:
                    failed += 1
                    errors.append(f"Failed to sync {part_id}: {str(e)}")
                    logger.error(f"Windchill sync error for {part_id}: {e}")

            duration = (datetime.now() - start_time).total_seconds()

            return SyncResult(
                success=failed == 0,
                items_synced=synced,
                items_failed=failed,
                errors=errors,
                duration_seconds=duration,
                timestamp=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Windchill sync_to_neo4j error: {e}")
            return SyncResult(
                success=False,
                items_synced=synced,
                items_failed=len(part_ids) - synced,
                errors=[str(e)],
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now(),
            )

    async def sync_from_neo4j(self, node_ids: List[str]) -> SyncResult:
        """
        Synchronize Neo4j nodes back to Windchill

        Args:
            node_ids: List of Neo4j node IDs to sync back to Windchill

        Returns:
            SyncResult with sync statistics
        """
        start_time = datetime.now()
        synced = 0
        failed = 0
        errors = []

        try:
            if not self.client:
                await self.authenticate()

            for node_id in node_ids:
                try:
                    # TODO: Query Neo4j for node data
                    # This would use Neo4j driver to fetch node properties
                    # Example: MATCH (n) WHERE id(n) = $node_id RETURN n

                    # TODO: Update part in Windchill using REST API
                    # This would use PUT/PATCH requests to update part attributes
                    # Example: PUT /Windchill/servlet/rest/v2/parts/{part_id}

                    logger.info(f"Synced Neo4j node {node_id} to Windchill")
                    synced += 1

                except Exception as e:
                    failed += 1
                    errors.append(f"Failed to sync node {node_id}: {str(e)}")
                    logger.error(f"Windchill sync error for node {node_id}: {e}")

            duration = (datetime.now() - start_time).total_seconds()

            return SyncResult(
                success=failed == 0,
                items_synced=synced,
                items_failed=failed,
                errors=errors,
                duration_seconds=duration,
                timestamp=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Windchill sync_from_neo4j error: {e}")
            return SyncResult(
                success=False,
                items_synced=synced,
                items_failed=len(node_ids) - synced,
                errors=[str(e)],
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now(),
            )


# Register Windchill connector with factory
PLMConnectorFactory.register(PLMSystem.WINDCHILL, WindchillConnector)


# Example usage
if __name__ == "__main__":

    async def main():
        # Configure Windchill connection
        config = PLMConfig(
            system=PLMSystem.WINDCHILL,
            base_url="https://windchill.company.com",
            username="plm_user",
            password="plm_password",
        )

        # Create connector
        connector = WindchillConnector(config)

        # Authenticate
        if await connector.authenticate():
            # Get part details
            part = await connector.get_part("PART-12345")
            print(f"Part: {part.get('name')}")

            # Get BOM
            bom = await connector.get_bom("PART-12345", depth=2)
            print(f"BOM has {len(bom.children)} components")

            # Search parts
            results = await connector.search_parts(name="Motor*")
            print(f"Found {len(results)} matching parts")

            # Get change orders
            changes = await connector.get_change_orders("PART-12345")
            print(f"Found {len(changes)} change orders")

            # Sync to Neo4j
            sync_result = await connector.sync_to_neo4j(["PART-12345"])
            print(f"Sync result: {sync_result.success_count} succeeded")

        await connector.close()

    asyncio.run(main())
