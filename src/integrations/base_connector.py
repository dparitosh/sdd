"""
Base PLM Connector Framework
Abstract interface for connecting to PLM systems (Teamcenter, Windchill, SAP, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio
from loguru import logger


class PLMSystem(Enum):
    """Supported PLM systems"""
    TEAMCENTER = "teamcenter"
    WINDCHILL = "windchill"
    THREE_DEXPERIENCE = "3dexperience"
    SAP_PLM = "sap_plm"
    ARAS = "aras"
    CUSTOM = "custom"


class SyncDirection(Enum):
    """Data synchronization direction"""
    PLM_TO_NEO4J = "plm_to_neo4j"
    NEO4J_TO_PLM = "neo4j_to_plm"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class PLMConfig:
    """Configuration for PLM connection"""
    system_type: PLMSystem
    base_url: str
    username: str
    password: str
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    auth_type: str = "basic"  # basic, oauth2, sso
    timeout: int = 30
    retry_count: int = 3
    verify_ssl: bool = True


@dataclass
class BOMItem:
    """Bill of Materials item"""
    part_id: str
    part_number: str
    part_name: str
    revision: str
    quantity: float
    unit: str
    parent_id: Optional[str] = None
    children: List['BOMItem'] = None
    attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.attributes is None:
            self.attributes = {}


@dataclass
class SyncResult:
    """Result of a synchronization operation"""
    success: bool
    items_synced: int
    items_failed: int
    errors: List[str]
    duration_seconds: float
    timestamp: datetime


class BasePLMConnector(ABC):
    """
    Abstract base class for PLM connectors
    Implement this for each PLM system (Teamcenter, Windchill, etc.)
    """
    
    def __init__(self, config: PLMConfig):
        self.config = config
        self.is_authenticated = False
        self._session = None
        logger.info(f"Initializing {config.system_type.value} connector")
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the PLM system
        Returns True if successful
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from the PLM system
        Returns True if successful
        """
        pass
    
    @abstractmethod
    async def get_part(self, part_id: str) -> Optional[Dict[str, Any]]:
        """
        Get part details by ID
        
        Args:
            part_id: Unique part identifier
            
        Returns:
            Dictionary with part details or None if not found
        """
        pass
    
    @abstractmethod
    async def get_bom(self, part_id: str, depth: int = 1) -> Optional[BOMItem]:
        """
        Get Bill of Materials for a part
        
        Args:
            part_id: Root part ID
            depth: How many levels deep to traverse (1 = immediate children only)
            
        Returns:
            BOMItem tree or None if not found
        """
        pass
    
    @abstractmethod
    async def search_parts(self, query: str, filters: Optional[Dict] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for parts
        
        Args:
            query: Search query string
            filters: Additional filters (type, status, etc.)
            limit: Maximum number of results
            
        Returns:
            List of matching parts
        """
        pass
    
    @abstractmethod
    async def get_change_orders(self, since: datetime) -> List[Dict[str, Any]]:
        """
        Get change orders since a specific date
        
        Args:
            since: Get changes after this timestamp
            
        Returns:
            List of change orders
        """
        pass
    
    @abstractmethod
    async def sync_to_neo4j(self, part_ids: List[str]) -> SyncResult:
        """
        Synchronize PLM data to Neo4j
        
        Args:
            part_ids: List of part IDs to sync
            
        Returns:
            SyncResult with success/failure details
        """
        pass
    
    @abstractmethod
    async def sync_from_neo4j(self, node_ids: List[str]) -> SyncResult:
        """
        Synchronize Neo4j data back to PLM
        
        Args:
            node_ids: List of Neo4j node IDs to sync
            
        Returns:
            SyncResult with success/failure details
        """
        pass
    
    # Helper methods (can be overridden)
    
    async def test_connection(self) -> bool:
        """Test if the connection to PLM system is working"""
        try:
            if not self.is_authenticated:
                await self.authenticate()
            
            # Try a simple operation
            result = await self.search_parts("test", limit=1)
            return result is not None
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def batch_sync(self, part_ids: List[str], batch_size: int = 10) -> SyncResult:
        """
        Synchronize parts in batches to avoid overwhelming the system
        
        Args:
            part_ids: List of part IDs
            batch_size: Number of items per batch
            
        Returns:
            Aggregated SyncResult
        """
        start_time = datetime.now()
        total_synced = 0
        total_failed = 0
        all_errors = []
        
        for i in range(0, len(part_ids), batch_size):
            batch = part_ids[i:i + batch_size]
            logger.info(f"Syncing batch {i//batch_size + 1}: {len(batch)} items")
            
            result = await self.sync_to_neo4j(batch)
            total_synced += result.items_synced
            total_failed += result.items_failed
            all_errors.extend(result.errors)
            
            # Small delay between batches
            await asyncio.sleep(0.5)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return SyncResult(
            success=total_failed == 0,
            items_synced=total_synced,
            items_failed=total_failed,
            errors=all_errors,
            duration_seconds=duration,
            timestamp=datetime.now()
        )
    
    def _build_bom_tree(self, root_data: Dict, children_data: List[Dict]) -> BOMItem:
        """
        Helper to build BOM tree from flat data
        
        Args:
            root_data: Root part data
            children_data: List of child parts
            
        Returns:
            BOMItem tree
        """
        root = BOMItem(
            part_id=root_data.get('id'),
            part_number=root_data.get('number'),
            part_name=root_data.get('name'),
            revision=root_data.get('revision', 'A'),
            quantity=1.0,
            unit=root_data.get('unit', 'EA'),
            attributes=root_data.get('attributes', {})
        )
        
        for child_data in children_data:
            child = BOMItem(
                part_id=child_data.get('id'),
                part_number=child_data.get('number'),
                part_name=child_data.get('name'),
                revision=child_data.get('revision', 'A'),
                quantity=child_data.get('quantity', 1.0),
                unit=child_data.get('unit', 'EA'),
                parent_id=root.part_id,
                attributes=child_data.get('attributes', {})
            )
            root.children.append(child)
        
        return root


class PLMConnectorFactory:
    """Factory for creating PLM connectors"""
    
    _connectors = {}
    
    @classmethod
    def register(cls, system_type: PLMSystem, connector_class):
        """Register a connector implementation"""
        cls._connectors[system_type] = connector_class
    
    @classmethod
    def create(cls, config: PLMConfig) -> BasePLMConnector:
        """Create a connector instance"""
        connector_class = cls._connectors.get(config.system_type)
        
        if not connector_class:
            raise ValueError(f"No connector registered for {config.system_type}")
        
        return connector_class(config)
    
    @classmethod
    def list_supported_systems(cls) -> List[str]:
        """List all registered PLM systems"""
        return [system.value for system in cls._connectors.keys()]


# Example usage in comments:
"""
# Create connector
config = PLMConfig(
    system_type=PLMSystem.TEAMCENTER,
    base_url="https://plm.company.com",
    username="admin",
    password="secret",
    auth_type="oauth2"
)

connector = PLMConnectorFactory.create(config)

# Authenticate
await connector.authenticate()

# Get BOM
bom = await connector.get_bom("PART-12345", depth=3)

# Sync to Neo4j
result = await connector.sync_to_neo4j(["PART-12345", "PART-67890"])
print(f"Synced {result.items_synced} items in {result.duration_seconds}s")
"""
