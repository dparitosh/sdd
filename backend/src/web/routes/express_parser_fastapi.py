"""
EXPRESS Parser REST API
============================================================================
FastAPI routes for EXPRESS schema parsing and analysis.
Provides RESTful endpoints for parsing, querying, and exporting EXPRESS schemas.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body, UploadFile, File
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field
from src.web.dependencies import get_api_key

from src.parsers.express import (
    ExpressParser,
    ExpressAnalyzer,
    ExpressNeo4jConverter,
    ExpressExporter,
    ExpressSchema,
    ParseResult,
    DirectoryParseResult,
    get_express_file_info,
)


# ============================================================================
# Path Safety
# ============================================================================

def _repo_root() -> Path:
    """backend/src/web/routes -> backend/src/web -> backend/src -> backend -> repo"""
    return Path(__file__).resolve().parents[4]


_ALLOWED_EXTENSIONS = {".exp", ".stp", ".step", ".stpx"}


def _resolve_safe_express_path(user_path: str) -> Path:
    """Resolve and validate a user-supplied path against allowed roots.

    Raises HTTPException 400 on path-traversal or disallowed extension.
    """
    root = _repo_root()
    p = Path(user_path)

    if not p.is_absolute():
        p = (root / p).resolve()
    else:
        p = p.resolve()

    allowed_roots = [
        (root / "smrlv12").resolve(),
        (root / "data").resolve(),
        (root / "backend" / "data").resolve(),
    ]

    if not any(str(p).startswith(str(ar)) for ar in allowed_roots):
        raise HTTPException(
            status_code=400,
            detail=(
                "Path is not under an allowed root. "
                f"Allowed roots: {', '.join(str(ar) for ar in allowed_roots)}"
            ),
        )

    if p.suffix.lower() not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{p.suffix}'. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}",
        )

    return p


# Create router
router = APIRouter(
    prefix="/express",
    tags=["EXPRESS Parser"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_api_key)],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class ParseFileRequest(BaseModel):
    """Request to parse an EXPRESS file"""
    file_path: str = Field(..., description="Absolute path to EXPRESS file")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "D:/MBSEsmrl/smrlv12/data/modules/ap239_product_life_cycle_support/arm.exp"
            }
        }


class ParseDirectoryRequest(BaseModel):
    """Request to parse a directory of EXPRESS files"""
    directory: str = Field(..., description="Directory path to search")
    recursive: bool = Field(default=True, description="Search subdirectories")
    pattern: str = Field(default="*.exp", description="File pattern to match")


class ParseContentRequest(BaseModel):
    """Request to parse EXPRESS content from string"""
    content: str = Field(..., description="EXPRESS schema content")
    source_name: str = Field(default="inline", description="Name for the source")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "SCHEMA test_schema;\n  ENTITY Example;\n    name : STRING;\n  END_ENTITY;\nEND_SCHEMA;",
                "source_name": "inline_test"
            }
        }


class CypherGenerationRequest(BaseModel):
    """Request to generate Cypher from schema"""
    schema_data: Dict[str, Any] = Field(..., description="Schema data from parse result")
    label_prefix: str = Field(default="", description="Prefix for Neo4j labels")
    include_relationships: bool = Field(default=True, description="Include relationship statements")


class EntityQueryRequest(BaseModel):
    """Request to query entities"""
    schema_data: Dict[str, Any] = Field(..., description="Schema data")
    entity_name: Optional[str] = Field(default=None, description="Specific entity name")
    supertype: Optional[str] = Field(default=None, description="Filter by supertype")
    include_abstract: bool = Field(default=True, description="Include abstract entities")


class ExportRequest(BaseModel):
    """Request to export schema"""
    schema_data: Dict[str, Any] = Field(..., description="Schema data from parse result")
    format: str = Field(default="json", description="Export format: json, markdown, graphml")


# ============================================================================
# Parse Endpoints
# ============================================================================

@router.post("/parse/file", response_model=Dict[str, Any])
async def parse_file(request: ParseFileRequest) -> Dict[str, Any]:
    """
    Parse an EXPRESS schema file from the filesystem.
    
    Returns parsed schema with entities, types, imports, and metadata.
    """
    parser = ExpressParser()
    safe_path = _resolve_safe_express_path(request.file_path)
    result = parser.parse_file(str(safe_path))
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return {
        "success": True,
        "schema": result.parsed_schema.model_dump() if result.parsed_schema else None,
        "warnings": result.warnings,
        "parse_time_ms": result.parse_time_ms,
    }


@router.post("/parse/content", response_model=Dict[str, Any])
async def parse_content(request: ParseContentRequest) -> Dict[str, Any]:
    """
    Parse EXPRESS schema content from a string.
    
    Useful for parsing inline schemas or content from other sources.
    """
    parser = ExpressParser()
    result = parser.parse_string(request.content, request.source_name)
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return {
        "success": True,
        "schema": result.parsed_schema.model_dump() if result.parsed_schema else None,
        "warnings": result.warnings,
        "parse_time_ms": result.parse_time_ms,
    }


@router.post("/parse/upload", response_model=Dict[str, Any])
async def parse_upload(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Parse an uploaded EXPRESS file.
    
    Accepts .exp file upload and returns parsed schema.
    """
    if not file.filename or not file.filename.endswith('.exp'):
        raise HTTPException(status_code=400, detail="File must have .exp extension")
    
    content = await file.read()
    content_str = content.decode('utf-8', errors='replace')
    
    parser = ExpressParser()
    result = parser.parse_string(content_str, file.filename)
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return {
        "success": True,
        "filename": file.filename,
        "schema": result.parsed_schema.model_dump() if result.parsed_schema else None,
        "warnings": result.warnings,
        "parse_time_ms": result.parse_time_ms,
    }


@router.post("/parse/directory", response_model=Dict[str, Any])
async def parse_directory(request: ParseDirectoryRequest) -> Dict[str, Any]:
    """
    Parse all EXPRESS files in a directory.
    
    Returns all parsed schemas and any errors encountered.
    """
    parser = ExpressParser()
    result = parser.parse_directory(
        request.directory,
        recursive=request.recursive,
        pattern=request.pattern
    )
    
    # Convert schemas to dicts
    schemas_dict = {
        name: schema.model_dump()
        for name, schema in result.schemas.items()
    }
    
    return {
        "directory": result.directory,
        "total_files": result.total_files,
        "successful": result.successful,
        "failed": result.failed,
        "schemas": schemas_dict,
        "errors": result.errors,
        "parse_time_ms": result.parse_time_ms,
    }


# ============================================================================
# Info & Query Endpoints
# ============================================================================

@router.get("/info", response_model=Dict[str, Any])
async def get_file_info(
    file_path: str = Query(..., description="Path to EXPRESS file")
) -> Dict[str, Any]:
    """
    Get basic info about an EXPRESS file without full parsing.
    
    Quick inspection of file size, schema name, and estimated counts.
    """
    safe_path = _resolve_safe_express_path(file_path)
    return get_express_file_info(str(safe_path))


@router.post("/query/entities", response_model=Dict[str, Any])
async def query_entities(request: EntityQueryRequest) -> Dict[str, Any]:
    """
    Query entities from a parsed schema.
    
    Filter by name, supertype, or abstract status.
    """
    # Reconstruct schema from dict
    schema = ExpressSchema(**request.schema_data)
    
    entities = list(schema.entities.values())
    
    # Apply filters
    if request.entity_name:
        entities = [e for e in entities if e.name.lower() == request.entity_name.lower()]
    
    if request.supertype:
        entities = [e for e in entities if e.supertype == request.supertype]
    
    if not request.include_abstract:
        entities = [e for e in entities if not e.is_abstract]
    
    return {
        "count": len(entities),
        "entities": [e.model_dump() for e in entities],
    }


@router.post("/query/types", response_model=Dict[str, Any])
async def query_types(
    schema_data: Dict[str, Any] = Body(...),
    kind: Optional[str] = Query(default=None, description="Filter by type kind: SELECT, ENUMERATION, ALIAS")
) -> Dict[str, Any]:
    """
    Query types from a parsed schema.
    
    Filter by type kind (SELECT, ENUMERATION, ALIAS, AGGREGATE).
    """
    schema = ExpressSchema(**schema_data)
    
    types = list(schema.types.values())
    
    if kind:
        types = [t for t in types if t.kind.upper() == kind.upper()]
    
    return {
        "count": len(types),
        "types": [t.model_dump() for t in types],
    }


# ============================================================================
# Analysis Endpoints
# ============================================================================

@router.post("/analyze/statistics", response_model=Dict[str, Any])
async def analyze_statistics(
    schema_data: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Get comprehensive statistics for a parsed schema.
    
    Returns counts for entities, types, attributes, and more.
    """
    schema = ExpressSchema(**schema_data)
    return ExpressAnalyzer.get_schema_statistics(schema)


@router.post("/analyze/inheritance", response_model=Dict[str, Any])
async def analyze_inheritance(
    schema_data: Dict[str, Any] = Body(...),
    root_entity: Optional[str] = Query(default=None, description="Root entity for subtree")
) -> Dict[str, Any]:
    """
    Get inheritance tree for entities.
    
    Returns hierarchical view of entity inheritance relationships.
    """
    schema = ExpressSchema(**schema_data)
    return ExpressAnalyzer.get_inheritance_tree(schema, root_entity)


@router.post("/analyze/type-usage", response_model=Dict[str, Any])
async def analyze_type_usage(
    schema_data: Dict[str, Any] = Body(...),
    type_name: str = Query(..., description="Type name to search for")
) -> Dict[str, Any]:
    """
    Find all entities that reference a specific type.
    """
    schema = ExpressSchema(**schema_data)
    referencing = ExpressAnalyzer.get_type_references(schema, type_name)
    
    return {
        "type_name": type_name,
        "referencing_entities": referencing,
        "count": len(referencing),
    }


@router.post("/analyze/select-usage", response_model=Dict[str, Any])
async def analyze_select_usage(
    schema_data: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Map SELECT types to the entities that use them.
    """
    schema = ExpressSchema(**schema_data)
    usage = ExpressAnalyzer.get_select_type_usage(schema)
    
    return {
        "select_types": usage,
        "total_select_types": len(usage),
    }


# ============================================================================
# Export Endpoints
# ============================================================================

@router.post("/export/json")
async def export_json(
    schema_data: Dict[str, Any] = Body(...),
    pretty: bool = Query(default=True, description="Pretty print JSON")
) -> Response:
    """
    Export schema to JSON format.
    """
    schema = ExpressSchema(**schema_data)
    json_content = ExpressExporter.to_json(schema, pretty=pretty)
    
    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{schema.name}.json"'
        }
    )


@router.post("/export/markdown")
async def export_markdown(
    schema_data: Dict[str, Any] = Body(...)
) -> Response:
    """
    Export schema documentation to Markdown format.
    """
    schema = ExpressSchema(**schema_data)
    md_content = ExpressExporter.to_markdown(schema)
    
    return Response(
        content=md_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{schema.name}.md"'
        }
    )


@router.post("/export/graphml")
async def export_graphml(
    schema_data: Dict[str, Any] = Body(...)
) -> Response:
    """
    Export schema to GraphML format for visualization.
    """
    schema = ExpressSchema(**schema_data)
    graphml_content = ExpressExporter.to_graphml(schema)
    
    return Response(
        content=graphml_content,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{schema.name}.graphml"'
        }
    )


# ============================================================================
# Neo4j Integration Endpoints
# ============================================================================

@router.post("/neo4j/cypher", response_model=Dict[str, Any])
async def generate_cypher(request: CypherGenerationRequest) -> Dict[str, Any]:
    """
    Generate Cypher statements to create schema in Neo4j.
    
    Returns list of MERGE statements for schema, entities, types, and relationships.
    """
    schema = ExpressSchema(**request.schema_data)
    statements = ExpressNeo4jConverter.schema_to_cypher(
        schema,
        label_prefix=request.label_prefix,
        include_relationships=request.include_relationships
    )
    
    return {
        "schema_name": schema.name,
        "statement_count": len(statements),
        "statements": statements,
    }


@router.post("/neo4j/graph", response_model=Dict[str, Any])
async def schema_to_graph(
    schema_data: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Convert schema to generic nodes and edges format.
    
    Returns structure that can be easily imported into graph databases.
    """
    schema = ExpressSchema(**schema_data)
    return ExpressNeo4jConverter.schema_to_nodes_and_edges(schema)


# ============================================================================
# Health & Info
# ============================================================================

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "EXPRESS Parser API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/")
async def api_info() -> Dict[str, Any]:
    """API information"""
    return {
        "name": "EXPRESS Parser API",
        "version": "1.0.0",
        "description": "RESTful API for parsing and analyzing ISO 10303-11 EXPRESS schemas",
        "endpoints": {
            "parse": {
                "/parse/file": "Parse EXPRESS file from filesystem",
                "/parse/content": "Parse EXPRESS content from string",
                "/parse/upload": "Parse uploaded EXPRESS file",
                "/parse/directory": "Parse all EXPRESS files in directory",
            },
            "query": {
                "/info": "Get file info without full parsing",
                "/query/entities": "Query entities from parsed schema",
                "/query/types": "Query types from parsed schema",
            },
            "analyze": {
                "/analyze/statistics": "Get schema statistics",
                "/analyze/inheritance": "Get inheritance tree",
                "/analyze/type-usage": "Find type references",
                "/analyze/select-usage": "Map SELECT type usage",
            },
            "export": {
                "/export/json": "Export to JSON",
                "/export/markdown": "Export to Markdown",
                "/export/graphml": "Export to GraphML",
            },
            "neo4j": {
                "/neo4j/cypher": "Generate Cypher statements",
                "/neo4j/graph": "Convert to nodes/edges format",
            },
        },
    }
