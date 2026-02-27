"""
EXPRESS Data Models
============================================================================
Pydantic models for representing EXPRESS schema structures.
Designed for serialization, validation, and API responses.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ExpressAttribute(BaseModel):
    """Represents an attribute within an ENTITY"""
    name: str = Field(..., description="Attribute name")
    type_ref: str = Field(..., description="Type reference")
    optional: bool = Field(default=False, description="Whether attribute is optional")
    is_list: bool = Field(default=False, description="Whether attribute is a collection")
    inverse: bool = Field(default=False, description="Whether this is an inverse attribute")
    derived: bool = Field(default=False, description="Whether this is a derived attribute")
    comment: Optional[str] = Field(default=None, description="Associated comment")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "requirement_text",
                "type_ref": "STRING",
                "optional": False,
                "is_list": False,
                "inverse": False,
                "derived": False,
            }
        }


class ExpressEntity(BaseModel):
    """Represents an ENTITY definition"""
    name: str = Field(..., description="Entity name")
    supertype: Optional[str] = Field(default=None, description="Parent entity name")
    subtypes: List[str] = Field(default_factory=list, description="Child entity names")
    attributes: List[ExpressAttribute] = Field(default_factory=list, description="Entity attributes")
    is_abstract: bool = Field(default=False, description="Whether entity is abstract")
    comment: Optional[str] = Field(default=None, description="Associated comment")
    
    @property
    def attribute_names(self) -> List[str]:
        """Get list of attribute names"""
        return [attr.name for attr in self.attributes]
    
    @property
    def required_attributes(self) -> List[ExpressAttribute]:
        """Get required (non-optional) attributes"""
        return [attr for attr in self.attributes if not attr.optional]
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Requirement",
                "supertype": "Product_definition",
                "subtypes": ["RequirementVersion"],
                "is_abstract": False,
                "attributes": [
                    {"name": "id", "type_ref": "STRING", "optional": False}
                ]
            }
        }


class ExpressType(BaseModel):
    """Represents a TYPE definition (SELECT, ENUMERATION, etc.)"""
    name: str = Field(..., description="Type name")
    kind: str = Field(..., description="Type kind: SELECT, ENUMERATION, ALIAS, AGGREGATE")
    base_type: Optional[str] = Field(default=None, description="Base type for aliases")
    options: List[str] = Field(default_factory=list, description="Options for SELECT or ENUM values")
    comment: Optional[str] = Field(default=None, description="Associated comment")
    
    @property
    def is_enumeration(self) -> bool:
        return self.kind == "ENUMERATION"
    
    @property
    def is_select(self) -> bool:
        return self.kind == "SELECT"
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "approval_status",
                "kind": "ENUMERATION",
                "options": ["approved", "rejected", "pending"]
            }
        }


class ExpressFunction(BaseModel):
    """Represents a FUNCTION or PROCEDURE"""
    name: str = Field(..., description="Function/Procedure name")
    kind: str = Field(..., description="FUNCTION or PROCEDURE")
    return_type: Optional[str] = Field(default=None, description="Return type for functions")
    parameters: List[Dict[str, str]] = Field(default_factory=list, description="Parameter list")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "validate_requirement",
                "kind": "FUNCTION",
                "return_type": "BOOLEAN",
                "parameters": [{"name": "req", "type": "Requirement"}]
            }
        }


class ExpressRule(BaseModel):
    """Represents a RULE definition"""
    name: str = Field(..., description="Rule name")
    applies_to: List[str] = Field(default_factory=list, description="Entities this rule applies to")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "unique_requirement_id",
                "applies_to": ["Requirement"]
            }
        }


class ExpressImport(BaseModel):
    """Represents a USE FROM import statement"""
    schema_name: str = Field(..., description="Imported schema name")
    comment: Optional[str] = Field(default=None, description="ISO reference comment")
    
    class Config:
        json_schema_extra = {
            "example": {
                "schema_name": "Analysis_assignment_arm",
                "comment": "ISO/TS 10303-1474"
            }
        }


class ExpressSchema(BaseModel):
    """Represents a complete EXPRESS SCHEMA"""
    name: str = Field(..., description="Schema name")
    source_file: str = Field(..., description="Source file path")
    imports: List[ExpressImport] = Field(default_factory=list, description="USE FROM imports")
    entities: Dict[str, ExpressEntity] = Field(default_factory=dict, description="Entity definitions")
    types: Dict[str, ExpressType] = Field(default_factory=dict, description="Type definitions")
    functions: Dict[str, ExpressFunction] = Field(default_factory=dict, description="Function definitions")
    rules: Dict[str, ExpressRule] = Field(default_factory=dict, description="Rule definitions")
    constants: Dict[str, str] = Field(default_factory=dict, description="Constant definitions")
    parsed_at: Optional[datetime] = Field(default=None, description="Parse timestamp")
    
    @property
    def entity_count(self) -> int:
        return len(self.entities)
    
    @property
    def type_count(self) -> int:
        return len(self.types)
    
    @property
    def import_count(self) -> int:
        return len(self.imports)
    
    @property
    def entity_names(self) -> List[str]:
        return list(self.entities.keys())
    
    @property
    def type_names(self) -> List[str]:
        return list(self.types.keys())
    
    def get_entity(self, name: str) -> Optional[ExpressEntity]:
        """Get entity by name (case-insensitive)"""
        return self.entities.get(name) or self.entities.get(name.lower())
    
    def get_type(self, name: str) -> Optional[ExpressType]:
        """Get type by name"""
        return self.types.get(name)
    
    def get_entities_by_supertype(self, supertype: str) -> List[ExpressEntity]:
        """Get all entities inheriting from a supertype"""
        return [e for e in self.entities.values() if e.supertype == supertype]
    
    def to_summary(self) -> Dict[str, Any]:
        """Return a summary without full details"""
        return {
            "name": self.name,
            "source_file": self.source_file,
            "entity_count": self.entity_count,
            "type_count": self.type_count,
            "import_count": self.import_count,
            "parsed_at": self.parsed_at.isoformat() if self.parsed_at else None,
        }
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Ap239_product_life_cycle_support_arm",
                "source_file": "smrlv12/data/modules/ap239_product_life_cycle_support/arm.exp",
                "entity_count": 50,
                "type_count": 30,
                "import_count": 15,
            }
        }


class ParseResult(BaseModel):
    """Result of parsing operation"""
    success: bool = Field(..., description="Whether parsing succeeded")
    parsed_schema: Optional[ExpressSchema] = Field(default=None, description="Parsed schema if successful")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Parse warnings")
    parse_time_ms: float = Field(default=0, description="Parse time in milliseconds")


class DirectoryParseResult(BaseModel):
    """Result of parsing a directory"""
    directory: str = Field(..., description="Parsed directory path")
    total_files: int = Field(default=0, description="Total EXPRESS files found")
    successful: int = Field(default=0, description="Successfully parsed files")
    failed: int = Field(default=0, description="Failed to parse files")
    schemas: Dict[str, ExpressSchema] = Field(default_factory=dict, description="Parsed schemas")
    errors: List[Dict[str, str]] = Field(default_factory=list, description="Parse errors")
    parse_time_ms: float = Field(default=0, description="Total parse time in milliseconds")
