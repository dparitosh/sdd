"""
ISO 10303-4443 SMRL Adapter - Convert Neo4j graph data to SMRL format
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class SMRLAdapter:
    """
    Adapter to convert Neo4j node data to ISO SMRL compliant format.
    Maps UML/SysML elements to SMRL resource types.
    """

    # UML/SysML to SMRL resource type mapping
    SMRL_TYPE_MAPPING = {
        "Class": "AccessibleModelTypeConstituent",
        "Package": "BreakdownElement",
        "Property": "PropertyDefinition",
        "Port": "InterfacePortType",
        "InstanceSpecification": "AccessibleModelInstanceConstituent",
        "Slot": "PropertyValue",
        "Association": "Association",
        "Constraint": "Constraint",
        "Comment": "LocalizedString",
        "Requirement": "Requirement",
        "ModelInstance": "ModelInstance",
        "Study": "Study",
        "ActualActivity": "ActualActivity",
        "AssociativeModelNetwork": "AssociativeModelNetwork",
        "ModelType": "ModelType",
        "Method": "Method",
        "Result": "Result",
        "Verification": "Verification",
        # AP242 Types
        "Part": "Part",
        "PartVersion": "PartVersion",
        "Assembly": "Assembly",
        "GeometricModel": "GeometricModel",
        "ShapeRepresentation": "ShapeRepresentation",
        "Material": "Material",
        # AP239 Types
        "Document": "Document",
        "Activity": "Activity",
        "WorkOrder": "WorkOrder",
        "Observation": "Observation",
        "Person": "Person",
        "Organization": "Organization",
        "Approval": "Approval",
        "VersionChain": "VersionChain",
        "VersionPoint": "VersionPoint",
    }

    @classmethod
    def to_smrl_resource(
        cls,
        node_data: Dict[str, Any],
        node_labels: List[str],
        strict_schema: bool = False,
    ) -> Dict[str, Any]:
        """
        Convert Neo4j node to SMRL resource format.

        Args:
            node_data: Dictionary of node properties from Neo4j
            node_labels: List of node labels (e.g., ['Class'])
            strict_schema: If True, use strict ISO SMRL field names (camelCase)

        Returns:
            SMRL-compliant resource dictionary
        """
        # Get primary label (first non-internal label)
        primary_label = next(
            (label for label in node_labels if not label.startswith("_")), None
        )

        # Get SMRL type
        smrl_type = node_data.get("smrl_type") or cls.SMRL_TYPE_MAPPING.get(
            primary_label, primary_label
        )

        # Get UID
        uid = node_data.get("uid", node_data.get("id", node_data.get("xmi_id")))

        # Build SMRL resource with official schema field names
        if strict_schema:
            resource = {
                "$href": node_data.get("href", f"/api/v1/{smrl_type}/{uid}"),
                "Identifiers": cls._build_identifiers(node_data, uid),
                "CreatedOn": cls._format_datetime(node_data.get("created_on", "")),
                "LastModified": cls._format_datetime(
                    node_data.get("last_modified", "")
                ),
                "CreatedBy": cls._build_person_reference(
                    node_data.get("created_by", "unknown")
                ),
                "ModifiedBy": cls._build_person_reference(
                    node_data.get("modified_by", "unknown")
                ),
                "VersionIdentifiers": cls._build_version_identifiers(node_data),
            }

            # Add Names (optional but recommended)
            if "name" in node_data and node_data["name"]:
                resource["Names"] = [
                    {"String": node_data["name"], "Context": "default"}
                ]

            # Add Descriptions (optional)
            descriptions = cls._build_descriptions(node_data)
            if descriptions:
                resource["Descriptions"] = descriptions
        else:
            # Simplified format for backward compatibility
            resource = {
                "uid": uid,
                "href": node_data.get("href", f"/api/v1/{smrl_type}/{uid}"),
                "smrl_type": smrl_type,
                "name": node_data.get("name", ""),
            }

            # Add descriptions (SMRL uses LocalizedString array)
            descriptions = cls._build_descriptions(node_data)
            if descriptions:
                resource["descriptions"] = descriptions

            # Add metadata
            if "created_on" in node_data:
                resource["created_on"] = cls._format_datetime(node_data["created_on"])
            if "last_modified" in node_data:
                resource["last_modified"] = cls._format_datetime(
                    node_data["last_modified"]
                )
            if "created_by" in node_data:
                resource["created_by"] = node_data["created_by"]
            if "modified_by" in node_data:
                resource["modified_by"] = node_data["modified_by"]

        # Add type-specific fields
        resource.update(cls._get_type_specific_fields(primary_label, node_data))

        return resource

    @classmethod
    def _build_identifiers(
        cls, node_data: Dict[str, Any], uid: str
    ) -> List[Dict[str, str]]:
        """Build SMRL Identifiers array (required field)."""
        identifiers = []

        # Primary UID
        identifiers.append({"String": uid, "Context": "uid"})

        # Add XMI ID if available
        if "xmi_id" in node_data and node_data["xmi_id"]:
            identifiers.append({"String": node_data["xmi_id"], "Context": "xmi"})

        return identifiers

    @classmethod
    def _build_person_reference(cls, person_id: str) -> Dict[str, str]:
        """Build SMRL PersonOrOrganizationItemReference."""
        return {"$ref": f"/api/v1/Person/{person_id}"}

    @classmethod
    def _build_version_identifiers(
        cls, node_data: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Build SMRL VersionIdentifiers array (required field)."""
        # For now, use a simple version identifier
        # In a full implementation, this would link to VersionChain/VersionPoint
        version = node_data.get("version", "1.0")
        return [{"String": str(version), "Context": "version"}]

    @classmethod
    def _build_descriptions(
        cls, node_data: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """Build SMRL descriptions array from various comment/description fields."""
        descriptions = []

        # Handle embedded descriptions array
        if "descriptions" in node_data and isinstance(node_data["descriptions"], list):
            return node_data["descriptions"]

        # Build from legacy fields
        if "documentation" in node_data and node_data["documentation"]:
            descriptions.append({"language": "en", "text": node_data["documentation"]})

        if "body" in node_data and node_data["body"]:  # For Comment nodes
            descriptions.append({"language": "en", "text": node_data["body"]})

        return descriptions if descriptions else None

    @classmethod
    def _format_datetime(cls, dt: Any) -> str:
        """Format datetime to ISO 8601 string."""
        if isinstance(dt, str):
            return dt
        if hasattr(dt, "isoformat"):
            return dt.isoformat()
        return str(dt)

    @classmethod
    def _get_type_specific_fields(
        cls, node_type: str, node_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get type-specific SMRL fields."""
        fields = {}

        if node_type == "Class":
            # AccessibleModelTypeConstituent specific fields
            if "visibility" in node_data:
                fields["visibility"] = node_data["visibility"]
            if "isAbstract" in node_data:
                fields["is_abstract"] = node_data["isAbstract"]

        elif node_type == "Property":
            # PropertyDefinition specific fields
            if "type" in node_data:
                fields["value_type"] = node_data["type"]
            if "default_value" in node_data:
                fields["property_value"] = node_data["default_value"]
            if "unit" in node_data:
                fields["unit"] = node_data["unit"]
            if "isDerived" in node_data:
                fields["is_derived"] = node_data["isDerived"]

        elif node_type == "Port":
            # InterfacePortType specific fields
            if "type" in node_data:
                fields["interface_type"] = node_data["type"]
            if "isConjugated" in node_data:
                fields["is_conjugated"] = node_data["isConjugated"]

        elif node_type == "Package":
            # BreakdownElement specific fields
            if "visibility" in node_data:
                fields["visibility"] = node_data["visibility"]

        elif node_type == "Requirement":
            # Requirement specific fields
            if "requirement_text" in node_data:
                fields["requirement_text"] = node_data["requirement_text"]
            if "priority" in node_data:
                fields["priority"] = node_data["priority"]
            if "status" in node_data:
                fields["status"] = node_data["status"]
            if "requirement_type" in node_data:
                fields["requirement_type"] = node_data["requirement_type"]

        elif node_type == "Person":
            # Person specific fields
            if "email" in node_data:
                fields["email"] = node_data["email"]
            if "role" in node_data:
                fields["role"] = node_data["role"]

        elif node_type == "Approval":
            # Approval specific fields
            if "status" in node_data:
                fields["approval_status"] = node_data["status"]
            if "approval_date" in node_data:
                fields["approval_date"] = cls._format_datetime(
                    node_data["approval_date"]
                )
            if "comments" in node_data:
                fields["approval_comments"] = node_data["comments"]

        # Add any remaining custom properties not covered above
        excluded_keys = {
            "uid",
            "href",
            "smrl_type",
            "name",
            "descriptions",
            "created_on",
            "last_modified",
            "created_by",
            "modified_by",
            "id",
            "xmi_id",
            "documentation",
            "body",
        }

        for key, value in node_data.items():
            if (
                key not in excluded_keys
                and key not in fields
                and not key.startswith("_")
            ):
                fields[key] = value

        return fields

    @classmethod
    def to_smrl_collection(
        cls, nodes: List[Dict], include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Convert list of nodes to SMRL collection format.

        Args:
            nodes: List of (node_data, node_labels) tuples
            include_metadata: Include pagination/count metadata

        Returns:
            SMRL collection response
        """
        resources = []
        for node_data, node_labels in nodes:
            resources.append(cls.to_smrl_resource(node_data, node_labels))

        result = {"resources": resources}

        if include_metadata:
            result["count"] = len(resources)
            result["total"] = len(resources)

        return result

    @classmethod
    def validate_smrl_resource(cls, resource: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate SMRL resource has required fields.

        Returns:
            (is_valid, list_of_errors)
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

        return (len(errors) == 0, errors)

    @classmethod
    def create_smrl_error_response(
        cls, status_code: int, message: str, details: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create SMRL-compliant error response."""
        error = {"error": {"code": status_code, "message": message}}

        if details:
            error["error"]["details"] = details

        return error


# Convenience functions for Flask routes
def neo4j_to_smrl(node_data: Dict, node_labels: List[str]) -> Dict:
    """Convert single Neo4j node to SMRL format."""
    return SMRLAdapter.to_smrl_resource(node_data, node_labels)


def neo4j_list_to_smrl(nodes: List[Tuple[Dict, List[str]]]) -> Dict:
    """Convert list of Neo4j nodes to SMRL collection."""
    return SMRLAdapter.to_smrl_collection(nodes)


def validate_smrl(resource: Dict) -> Tuple[bool, List[str]]:
    """Validate SMRL resource."""
    return SMRLAdapter.validate_smrl_resource(resource)
