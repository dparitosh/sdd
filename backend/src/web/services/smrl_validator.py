"""
ISO 10303-4443 SMRL Schema Validator
=====================================
Full OpenAPI/JSON Schema validation using DomainModel.json schema

This module provides comprehensive SMRL validation against the official
ISO 10303-4443 schema definition.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

try:
    from jsonschema import Draft7Validator

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    logger.warning("jsonschema not installed. Full schema validation disabled.")


class SMRLSchemaValidator:
    """
    Validates SMRL resources against ISO 10303-4443 OpenAPI schema.
    """

    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize validator with SMRL schema.

        Args:
            schema_path: Path to DomainModel.json. If None, uses default path.
        """
        self.schema: Optional[Dict] = None
        self.validators: Dict[str, Any] = {}
        self.schema_loaded = False

        if not JSONSCHEMA_AVAILABLE:
            logger.warning(
                "jsonschema package not available. Install with: pip install jsonschema"
            )
            return

        # Default schema path
        if schema_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            schema_path = str(
                project_root
                / "smrlv12"
                / "data"
                / "domain_models"
                / "mossec"
                / "DomainModel.json"
            )

        self._load_schema(schema_path)

    def _load_schema(self, schema_path: str):
        """Load and parse SMRL schema from JSON file."""
        try:
            with open(schema_path, "r") as f:
                self.schema = json.load(f)

            # Extract component schemas
            if "components" in self.schema and "schemas" in self.schema["components"]:
                self.schemas = self.schema["components"]["schemas"]
                logger.info(
                    f"Loaded SMRL schema with {len(self.schemas)} resource types"
                )

                # Pre-compile validators for common types
                for resource_type in [
                    "AccessibleModelTypeConstituent",
                    "AccessibleModelInstanceConstituent",
                    "BreakdownElement",
                    "PropertyDefinition",
                    "InterfacePortType",
                    "Requirement",
                    "Person",
                    "Organization",
                    "Approval",
                    "VersionChain",
                    "VersionPoint",
                ]:
                    self._compile_validator(resource_type)

                self.schema_loaded = True
            else:
                logger.error("Invalid schema structure: missing components/schemas")

        except FileNotFoundError:
            logger.error(f"SMRL schema not found at: {schema_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse SMRL schema: {e}")
        except Exception as e:
            logger.error(f"Error loading SMRL schema: {e}")

    def _compile_validator(self, resource_type: str):
        """Pre-compile JSON schema validator for a resource type."""
        if not self.schema_loaded or resource_type not in self.schemas:
            return

        try:
            # Build a ref path into the OpenAPI components tree.
            # Some schemas wrap the actual resource under a property named after the resource type.
            ref_path = f"#/components/schemas/{resource_type}"
            resource_schema = self.schemas[resource_type]
            if (
                "properties" in resource_schema
                and resource_type in resource_schema["properties"]
            ):
                ref_path = (
                    f"#/components/schemas/{resource_type}/properties/{resource_type}"
                )

            # Validate against a wrapper schema containing the full components tree.
            # This avoids deprecated RefResolver usage while still resolving $ref across components.
            wrapper_schema = {
                "$ref": ref_path,
                "components": {"schemas": self.schemas},
            }

            validator = Draft7Validator(wrapper_schema)
            self.validators[resource_type] = validator

        except Exception as e:
            logger.error(f"Failed to compile validator for {resource_type}: {e}")

    def validate_resource(
        self, resource: Dict[str, Any], resource_type: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate a SMRL resource against its schema.

        Args:
            resource: SMRL resource dictionary to validate
            resource_type: SMRL resource type (e.g., "AccessibleModelTypeConstituent")

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if not JSONSCHEMA_AVAILABLE:
            return self._basic_validation(resource)

        if not self.schema_loaded:
            logger.warning("Schema not loaded, falling back to basic validation")
            return self._basic_validation(resource)

        errors = []

        try:
            # Get or compile validator
            if resource_type not in self.validators:
                self._compile_validator(resource_type)

            validator = self.validators.get(resource_type)
            if not validator:
                return self._basic_validation(resource)

            # Validate against schema
            validation_errors = sorted(
                validator.iter_errors(resource), key=lambda e: e.path
            )

            for error in validation_errors:
                # Format error message with path
                path = ".".join(str(p) for p in error.path) if error.path else "root"
                errors.append(f"{path}: {error.message}")

            return (len(errors) == 0, errors)

        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return (False, [f"Validation error: {str(e)}"])

    def _basic_validation(self, resource: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Fallback basic validation when schema is not available.
        Checks only essential SMRL fields.
        """
        errors = []

        # Required fields
        if "uid" not in resource or not resource["uid"]:
            errors.append("Missing required field: uid")

        if "href" not in resource or not resource["href"]:
            errors.append("Missing required field: href")

        if "smrl_type" not in resource:
            errors.append("Missing required field: smrl_type")

        # Validate href format
        if "href" in resource and not resource["href"].startswith("/api/v1/"):
            errors.append(
                f"Invalid href format: {resource['href']} (should start with /api/v1/)"
            )

        # Validate required metadata fields
        if "created_on" not in resource:
            errors.append("Missing required field: created_on")

        if "last_modified" not in resource:
            errors.append("Missing required field: last_modified")

        return (len(errors) == 0, errors)

    def validate_collection(self, collection: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a SMRL collection response.

        Args:
            collection: SMRL collection dictionary

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check collection structure
        if "items" not in collection:
            errors.append("Missing 'items' array in collection")
            return (False, errors)

        if not isinstance(collection["items"], list):
            errors.append("'items' must be an array")
            return (False, errors)

        # Validate metadata
        if "total_count" not in collection:
            errors.append("Missing 'total_count' in collection metadata")

        # Validate each item
        for idx, item in enumerate(collection["items"]):
            resource_type = item.get("smrl_type")
            if not resource_type:
                errors.append(f"Item {idx}: Missing smrl_type")
                continue

            is_valid, item_errors = self.validate_resource(item, resource_type)
            if not is_valid:
                for err in item_errors:
                    errors.append(f"Item {idx} ({resource_type}): {err}")

        return (len(errors) == 0, errors)

    def get_resource_schema(self, resource_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the schema definition for a specific resource type.

        Args:
            resource_type: SMRL resource type

        Returns:
            Schema dictionary or None if not found
        """
        if not self.schema_loaded:
            return None

        return self.schemas.get(resource_type)

    def list_resource_types(self) -> List[str]:
        """
        Get list of all available SMRL resource types in schema.

        Returns:
            List of resource type names
        """
        if not self.schema_loaded:
            return []

        return list(self.schemas.keys())

    def get_required_fields(self, resource_type: str) -> List[str]:
        """
        Get list of required fields for a resource type.

        Args:
            resource_type: SMRL resource type

        Returns:
            List of required field names
        """
        if not self.schema_loaded or resource_type not in self.schemas:
            return []

        schema = self.schemas[resource_type]

        # Handle nested structure
        if "properties" in schema and resource_type in schema["properties"]:
            schema = schema["properties"][resource_type]

        return schema.get("required", [])


# Singleton instance
_validator_instance: Optional[SMRLSchemaValidator] = None


def get_smrl_validator() -> SMRLSchemaValidator:
    """
    Get singleton SMRL validator instance.

    Returns:
        SMRLSchemaValidator instance
    """
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = SMRLSchemaValidator()
    return _validator_instance


# Convenience functions
def validate_smrl_resource(
    resource: Dict[str, Any], resource_type: str
) -> Tuple[bool, List[str]]:
    """
    Validate a SMRL resource.

    Args:
        resource: SMRL resource dictionary
        resource_type: SMRL resource type

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    validator = get_smrl_validator()
    return validator.validate_resource(resource, resource_type)


def validate_smrl_collection(collection: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a SMRL collection.

    Args:
        collection: SMRL collection dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    validator = get_smrl_validator()
    return validator.validate_collection(collection)
