"""
ISO 10303-4443 SMRL Adapter - Convert Neo4j graph data to SMRL format.

DEPRECATED: This module re-exports from src.core.smrl_adapter.
Import directly from src.core.smrl_adapter for new code.
"""

# Re-export everything from canonical location for backward compatibility
from src.core.smrl_adapter import (  # noqa: F401
    SMRLAdapter,
    neo4j_list_to_smrl,
    neo4j_to_smrl,
    validate_smrl,
)
