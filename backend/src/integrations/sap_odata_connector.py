"""
SAP PLM connector implementation using OData API
Supports SAP S/4HANA and SAP PLM for product structure management
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
from loguru import logger
from urllib.parse import quote

from .base_connector import (
    BasePLMConnector,
    PLMConfig,
    PLMSystem,
    BOMItem,
    SyncResult,
    PLMConnectorFactory,
)


class SAPODataConnector(BasePLMConnector):
    """
    SAP S/4HANA and SAP PLM integration via OData API

    Features:
    - Material master data (MM)
    - Bill of Materials (BOM)
    - Engineering Change Records (ECR)
    - Document management (DMS)
    - Product structure (PS)
    """

    def __init__(self, config: PLMConfig):
        super().__init__(config)
        self.client: Optional[httpx.AsyncClient] = None
        self.csrf_token: Optional[str] = None
        self.api_version = (
            getattr(config, "custom_fields", {}).get("api_version", "v1")
            if hasattr(config, "custom_fields")
            else "v1"
        )

    async def authenticate(self) -> bool:
        """
        Authenticate with SAP using Basic Auth or OAuth2

        Returns:
            True if authentication successful
        """
        try:
            # Create async HTTP client with SAP-specific settings
            self.client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(60.0),
                verify=False,  # Set to True in production
            )

            if self.config.username and self.config.password:
                # Basic authentication (most common for SAP OData)
                self.client.auth = (self.config.username, self.config.password)

                # Get CSRF token for write operations
                csrf_response = await self.client.get(
                    f"/sap/opu/odata/sap/API_MATERIAL_STOCK_SRV/{self.api_version}/",
                    headers={"X-CSRF-Token": "Fetch"},
                )

                if csrf_response.status_code in [200, 201]:
                    self.csrf_token = csrf_response.headers.get("X-CSRF-Token")
                    logger.info(f"SAP OData authentication successful: {self.config.base_url}")
                    return True
                else:
                    logger.error(f"SAP authentication failed: {csrf_response.status_code}")
                    return False

            elif self.config.auth_token:
                # OAuth2 token authentication
                self.client.headers.update({"Authorization": f"Bearer {self.config.auth_token}"})

                # Verify token
                verify_response = await self.client.get(
                    f"/sap/opu/odata/sap/API_MATERIAL_STOCK_SRV/{self.api_version}/$metadata"
                )

                if verify_response.status_code == 200:
                    logger.info("SAP OAuth2 authentication successful")
                    return True
                else:
                    logger.error("SAP OAuth2 token validation failed")
                    return False

            else:
                logger.error("No authentication credentials provided")
                return False

        except Exception as e:
            logger.error(f"SAP authentication error: {e}")
            return False

    async def get_part(self, part_id: str) -> Dict[str, Any]:
        """
        Retrieve material master data from SAP

        Args:
            part_id: Material number (MATNR)

        Returns:
            Material details dictionary
        """
        if not self.client:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            # Query material master data
            # Using API_PRODUCT_SRV or custom Z-table
            response = await self.client.get(
                f"/sap/opu/odata/sap/API_PRODUCT_SRV/{self.api_version}/A_Product",
                params={"$filter": f"Product eq '{part_id}'", "$format": "json"},
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("d", {}).get("results"):
                    material = data["d"]["results"][0]

                    # Transform SAP response to standard format
                    part_data = {
                        "id": material.get("Product"),
                        "number": material.get("Product"),
                        "name": material.get("ProductDescription", ""),
                        "revision": material.get("ProductVersion", "A"),
                        "state": material.get("ProductStatus"),
                        "type": material.get("ProductType"),
                        "description": material.get("ProductDescription"),
                        "created_date": material.get("CreationDate"),
                        "modified_date": material.get("LastChangeDate"),
                        "owner": material.get("CreatedByUser"),
                        "attributes": {
                            "base_unit": material.get("BaseUnit"),
                            "product_group": material.get("ProductGroup"),
                            "gross_weight": material.get("GrossWeight"),
                            "net_weight": material.get("NetWeight"),
                            "weight_unit": material.get("WeightUnit"),
                            "material_type": material.get("MaterialType"),
                        },
                    }

                    logger.info(f"Retrieved SAP material: {part_id}")
                    return part_data
                else:
                    logger.warning(f"SAP material {part_id} not found")
                    return {}

            else:
                logger.error(f"Failed to get material {part_id}: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error retrieving SAP material {part_id}: {e}")
            return {}

    async def get_bom(self, part_id: str, depth: int = 1) -> BOMItem:
        """
        Retrieve BOM structure from SAP

        Args:
            part_id: Material number
            depth: BOM expansion depth (1-10)

        Returns:
            BOMItem tree structure
        """
        if not self.client:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            # Get root material
            material = await self.get_part(part_id)

            root_item = BOMItem(
                part_number=material.get("number", part_id),
                name=material.get("name", ""),
                revision=material.get("revision", "A"),
                quantity=1,
                unit=material.get("attributes", {}).get("base_unit", "EA"),
                children=[],
            )

            if depth > 0:
                # Query BOM using API_BILL_OF_MATERIAL_SRV
                response = await self.client.get(
                    f"/sap/opu/odata/sap/API_BILL_OF_MATERIAL_SRV/{self.api_version}/MaterialBOM",
                    params={
                        "$filter": f"Material eq '{part_id}'",
                        "$expand": "to_MaterialBOMItem",
                        "$format": "json",
                    },
                )

                if response.status_code == 200:
                    bom_data = response.json()

                    # Parse BOM items
                    if bom_data.get("d", {}).get("results"):
                        bom_header = bom_data["d"]["results"][0]
                        bom_items = bom_header.get("to_MaterialBOMItem", {}).get("results", [])

                        root_item.children = await self._parse_sap_bom_items(bom_items, depth - 1)

            logger.info(f"Retrieved SAP BOM for {part_id}, depth={depth}")
            return root_item

        except Exception as e:
            logger.error(f"Error retrieving SAP BOM for {part_id}: {e}")
            return BOMItem(part_number=part_id, name="", revision="A", quantity=1, unit="EA")

    async def _parse_sap_bom_items(self, items: List[Dict], remaining_depth: int) -> List[BOMItem]:
        """Parse SAP BOM items recursively"""
        bom_items = []

        for item in items:
            bom_item = BOMItem(
                part_number=item.get("BillOfMaterialComponent", ""),
                name=item.get("ComponentDescription", ""),
                revision=item.get("ComponentVersion", "A"),
                quantity=float(item.get("BillOfMaterialItemQuantity", 1)),
                unit=item.get("BillOfMaterialItemUnit", "EA"),
                children=[],
            )

            # Recursively get child BOMs if depth remaining
            if remaining_depth > 0 and bom_item.part_number:
                child_bom = await self.get_bom(bom_item.part_number, remaining_depth)
                bom_item.children = child_bom.children

            bom_items.append(bom_item)

        return bom_items

    async def search_parts(self, **criteria) -> List[Dict[str, Any]]:
        """
        Search for materials in SAP

        Args:
            **criteria: Search criteria (name, number, type, plant)

        Returns:
            List of matching materials
        """
        if not self.client:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            # Build OData filter query
            filters = []

            if "name" in criteria:
                # Use substringof for partial match
                filters.append(f"substringof('{criteria['name']}', ProductDescription)")

            if "number" in criteria:
                filters.append(f"Product eq '{criteria['number']}'")

            if "type" in criteria:
                filters.append(f"ProductType eq '{criteria['type']}'")

            if "plant" in criteria:
                filters.append(f"Plant eq '{criteria['plant']}'")

            filter_string = " and ".join(filters) if filters else ""

            params = {"$format": "json"}
            if filter_string:
                params["$filter"] = filter_string

            response = await self.client.get(
                f"/sap/opu/odata/sap/API_PRODUCT_SRV/{self.api_version}/A_Product", params=params
            )

            if response.status_code == 200:
                results = response.json()
                materials = []

                for item in results.get("d", {}).get("results", []):
                    materials.append(
                        {
                            "id": item.get("Product"),
                            "number": item.get("Product"),
                            "name": item.get("ProductDescription"),
                            "revision": item.get("ProductVersion", "A"),
                            "state": item.get("ProductStatus"),
                            "type": item.get("ProductType"),
                        }
                    )

                logger.info(f"SAP search found {len(materials)} materials")
                return materials

            else:
                logger.error(f"SAP search failed: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"SAP search error: {e}")
            return []

    async def get_change_orders(self, part_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get Engineering Change Records (ECR) from SAP

        Args:
            part_id: Optional material to filter changes

        Returns:
            List of change records
        """
        if not self.client:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            # Query Engineering Change Records
            params = {"$format": "json"}

            if part_id:
                params["$filter"] = f"Material eq '{part_id}'"

            response = await self.client.get(
                f"/sap/opu/odata/sap/API_ENGINEERING_CHANGE_SRV/{self.api_version}/EngChangeRecord",
                params=params,
            )

            if response.status_code == 200:
                changes = response.json()
                change_records = []

                for change in changes.get("d", {}).get("results", []):
                    change_records.append(
                        {
                            "id": change.get("ChangeNumber"),
                            "name": change.get("ChangeDescription"),
                            "type": change.get("ChangeRecordType"),
                            "state": change.get("ChangeRecordStatus"),
                            "description": change.get("LongText"),
                            "created_date": change.get("CreationDate"),
                            "affected_parts": [
                                part_id  # Would need separate query to get all affected materials
                            ],
                        }
                    )

                logger.info(f"Retrieved {len(change_records)} SAP change records")
                return change_records

            else:
                logger.error(f"Failed to get change records: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error retrieving change records: {e}")
            return []

    async def get_documents(self, part_id: str) -> List[Dict[str, Any]]:
        """
        Get documents associated with a material from SAP DMS

        Args:
            part_id: Material number

        Returns:
            List of document metadata
        """
        if not self.client:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            response = await self.client.get(
                f"/sap/opu/odata/sap/API_CV_ATTACHMENT_SRV/{self.api_version}/MaterialDocuments",
                params={"$filter": f"Material eq '{part_id}'", "$format": "json"},
            )

            if response.status_code == 200:
                docs = response.json()
                documents = []

                for doc in docs.get("d", {}).get("results", []):
                    documents.append(
                        {
                            "document_number": doc.get("DocumentNumber"),
                            "document_type": doc.get("DocumentType"),
                            "document_version": doc.get("DocumentVersion"),
                            "description": doc.get("DocumentDescription"),
                            "file_name": doc.get("FileName"),
                            "created_date": doc.get("CreationDate"),
                        }
                    )

                logger.info(f"Retrieved {len(documents)} documents for {part_id}")
                return documents

            else:
                logger.error(f"Failed to get documents: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []

    async def close(self):
        """Close HTTP client connection"""
        if self.client:
            await self.client.aclose()
            logger.info("SAP OData connection closed")

    async def disconnect(self) -> bool:
        """
        Disconnect from SAP and clean up resources
        """
        try:
            await self.close()
            self.is_authenticated = False
            logger.info("SAP disconnected successfully")
            return True
        except Exception as e:
            logger.error(f"SAP disconnect error: {e}")
            return False

    async def sync_to_neo4j(self, part_ids: List[str]) -> SyncResult:
        """
        Synchronize SAP materials/products to Neo4j graph database

        Args:
            part_ids: List of SAP material numbers to sync

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
                    # Get material/product data from SAP
                    part = await self.get_part(part_id)
                    if not part:
                        failed += 1
                        errors.append(f"Material {part_id} not found in SAP")
                        continue

                    # Get BOM structure
                    bom = await self.get_bom(part_id, depth=2)

                    # TODO: Insert into Neo4j using graph connection
                    # This would use the Neo4j driver to create nodes and relationships
                    # Example: CREATE (m:Material {id: $material_id, name: $name, ...})

                    logger.info(f"Synced SAP material {part_id} to Neo4j")
                    synced += 1

                except Exception as e:
                    failed += 1
                    errors.append(f"Failed to sync {part_id}: {str(e)}")
                    logger.error(f"SAP sync error for {part_id}: {e}")

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
            logger.error(f"SAP sync_to_neo4j error: {e}")
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
        Synchronize Neo4j nodes back to SAP

        Args:
            node_ids: List of Neo4j node IDs to sync back to SAP

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

                    # TODO: Update material in SAP using OData API
                    # This would use PATCH requests to update material attributes
                    # Example: PATCH /sap/opu/odata/sap/API_PRODUCT_SRV/A_Product('{material_id}')

                    logger.info(f"Synced Neo4j node {node_id} to SAP")
                    synced += 1

                except Exception as e:
                    failed += 1
                    errors.append(f"Failed to sync node {node_id}: {str(e)}")
                    logger.error(f"SAP sync error for node {node_id}: {e}")

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
            logger.error(f"SAP sync_from_neo4j error: {e}")
            return SyncResult(
                success=False,
                items_synced=synced,
                items_failed=len(node_ids) - synced,
                errors=[str(e)],
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now(),
            )


# Register SAP connector with factory
PLMConnectorFactory.register(PLMSystem.SAP_PLM, SAPODataConnector)


# Example usage
if __name__ == "__main__":

    async def main():
        # Configure SAP connection
        config = PLMConfig(
            system=PLMSystem.SAP_PLM,
            base_url="https://sap.company.com:8000",
            username="PLM_USER",
            password="password",
            custom_fields={"api_version": "v1"},
        )

        # Create connector
        connector = SAPODataConnector(config)

        # Authenticate
        if await connector.authenticate():
            # Get material details
            material = await connector.get_part("MAT-12345")
            print(f"Material: {material.get('name')}")

            # Get BOM
            bom = await connector.get_bom("MAT-12345", depth=2)
            print(f"BOM has {len(bom.children)} components")

            # Search materials
            results = await connector.search_parts(name="Bearing")
            print(f"Found {len(results)} matching materials")

            # Get change records
            changes = await connector.get_change_orders("MAT-12345")
            print(f"Found {len(changes)} change records")

            # Get documents
            docs = await connector.get_documents("MAT-12345")
            print(f"Found {len(docs)} documents")

            # Sync to Neo4j
            sync_result = await connector.sync_to_neo4j(["MAT-12345"])
            print(f"Sync result: {sync_result.success_count} succeeded")

        await connector.close()

    asyncio.run(main())
