"""
ISO 10303-4443 SMRL Schema Validator.

DEPRECATED: This module re-exports from src.core.smrl_validator.
Import directly from src.core.smrl_validator for new code.
"""

# Re-export everything from canonical location for backward compatibility
from src.core.smrl_validator import (  # noqa: F401
    SMRLSchemaValidator,
    get_smrl_validator,
    validate_smrl_collection,
    validate_smrl_resource,
)
