"""
AP242 REST API Routes (FastAPI) - 3D Engineering and Manufacturing
==================================================================
Endpoints for Parts, Assemblies, Materials, and CAD Geometry

ISO 10303 AP242 provides 3D engineering capabilities including CAD models,
Bill of Materials (BOM), material specifications, and assembly structures.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Path
from pydantic import BaseModel, Field
from loguru import logger
import re

from src.web.services import get_neo4j_service
from src.web.dependencies import get_api_key
from src.web.app_fastapi import Neo4jJSONResponse

router = APIRouter()

# Valid status values
VALID_STATUSES = {
    "Released",
    "Development",
    "Obsolete",
    "Draft",
    "In Review",
    "Approved",
}


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class VersionInfo(BaseModel):
    version: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None


class MaterialInfo(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    spec: Optional[str] = None


class GeometryInfo(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    units: Optional[str] = None


class Part(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = "Unknown"
    description: Optional[str] = None
    part_number: Optional[str] = None
    status: Optional[str] = None
    versions: List[str] = []
    materials: List[str] = []
    requirements: List[str] = []


class PartsResponse(BaseModel):
    count: int
    parts: List[Part]


class PartDetail(BaseModel):
    id: Optional[str] = "Missing ID"
    name: Optional[str] = "Unknown"
    description: Optional[str] = None
    part_number: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    ap_level: Optional[int] = None
    ap_schema: Optional[str] = None
    versions: List[VersionInfo] = []
    materials: List[MaterialInfo] = []
    geometry: List[GeometryInfo] = []
    assemblies: List[str] = []
    requirements: List[str] = []
    approvals: List[str] = []


class ComponentInfo(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    part_number: Optional[str] = None


class BOMResponse(BaseModel):
    root_part: str
    assembly: Optional[str] = None
    components: List[ComponentInfo]


class Assembly(BaseModel):
    name: str
    type: Optional[str] = None
    component_count: Optional[int] = None
    parts: List[str] = []


class AssembliesResponse(BaseModel):
    count: int
    assemblies: List[Assembly]


class MaterialProperty(BaseModel):
    name: Optional[str] = None
    value: Optional[Any] = None
    unit: Optional[str] = None
    temperature: Optional[float] = None
    unit_name: Optional[str] = None


class Material(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    specification: Optional[str] = None
    properties: List[MaterialProperty] = []
    used_in_parts: List[str] = []
    ontology_classes: List[str] = []


class MaterialsResponse(BaseModel):
    count: int
    materials: List[Material]


class OntologyInfo(BaseModel):
    name: Optional[str] = None
    ontology: Optional[str] = None


class MaterialDetail(BaseModel):
    name: str
    material_type: Optional[str] = None
    specification: Optional[str] = None
    ap_level: Optional[int] = None
    ap_schema: Optional[str] = None
    properties: List[MaterialProperty] = []
    used_in_parts: List[str] = []
    ontology_classes: List[OntologyInfo] = []
    requirements: List[str] = []


class GeometricModel(BaseModel):
    name: str
    type: Optional[str] = None
    units: Optional[str] = None
    representations: List[str] = []
    parts: List[str] = []
    analyses: List[str] = []


class GeometryResponse(BaseModel):
    count: int
    geometry: List[GeometricModel]


class TypeBreakdown(BaseModel):
    total: int
    breakdown: Dict[str, int] = {}


class StatisticsResponse(BaseModel):
    ap_level: int
    ap_schema: str
    statistics: Dict[str, TypeBreakdown]


# ============================================================================
# PARTS ENDPOINTS
# ============================================================================


@router.get("/parts", response_model=PartsResponse, response_class=Neo4jJSONResponse)
async def get_parts(
    status: Optional[str] = Query(
        None, description="Filter by status (Released, Development, Obsolete)"
    ),
    search: Optional[str] = Query(None, description="Search in name and description"),
    api_key: str = Depends(get_api_key),
):
    """
    Get all parts with optional filtering

    Args:
        status: Filter by status (Released, Development, Obsolete)
        search: Text search in name and description

    Returns:
        Array of part objects with basic info
    """
    try:
        neo4j = get_neo4j_service()

        filters = []
        params = {}

        if status and status in VALID_STATUSES:
            filters.append("part.status = $status")
            params["status"] = status

        if search:
            # Escape regex metacharacters
            escaped_search = re.escape(search)
            filters.append("(part.name =~ $search OR part.description =~ $search)")
            params["search"] = f"(?i).*{escaped_search}.*"

        where_clause = " AND ".join(filters) if filters else "1=1"

        query = f"""
        MATCH (part:Part)
        WHERE part.ap_level = 2 AND {where_clause}
        OPTIONAL MATCH (part)-[:HAS_VERSION]->(v:PartVersion)
        OPTIONAL MATCH (part)-[:USES_MATERIAL]->(mat:Material)
        OPTIONAL MATCH (req:Requirement)-[:SATISFIED_BY_PART]->(part)
        RETURN part.id AS id,
               part.name AS name,
               part.description AS description,
               part.part_number AS part_number,
               part.status AS status,
               COLLECT(DISTINCT v.version) AS versions,
               COLLECT(DISTINCT mat.name) AS materials,
               COLLECT(DISTINCT req.name) AS satisfies_requirements
        ORDER BY part.part_number, part.name
        """

        results = neo4j.execute_query(query, params)

        parts = [
            {
                "id": r["id"],
                "name": r["name"] or "Unknown",
                "description": r["description"],
                "part_number": r["part_number"],
                "status": r["status"],
                "versions": [v for v in r["versions"] if v],
                "materials": [m for m in r["materials"] if m],
                "requirements": [req for req in r["satisfies_requirements"] if req],
            }
            for r in results
        ]

        return {"count": len(parts), "parts": parts}

    except Exception as e:
        logger.error(f"Error fetching parts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/parts/{part_id}", response_model=PartDetail, response_class=Neo4jJSONResponse
)
async def get_part_detail(
    part_id: str = Path(..., description="Part ID"), api_key: str = Depends(get_api_key)
):
    """
    Get detailed information about a specific part

    Args:
        part_id: Unique part identifier

    Returns:
        Part with all relationships (versions, materials, geometry, etc.)
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (part:Part {id: $part_id})
        OPTIONAL MATCH (part)-[:HAS_VERSION]->(v:PartVersion)
        OPTIONAL MATCH (part)-[:USES_MATERIAL]->(mat:Material)
        OPTIONAL MATCH (part)-[:HAS_GEOMETRY]->(geo:GeometricModel)
        OPTIONAL MATCH (asm:Assembly)-[:ASSEMBLES_WITH]->(part)
        OPTIONAL MATCH (req:Requirement)-[:SATISFIED_BY_PART]->(part)
        OPTIONAL MATCH (appr:Approval)-[:APPROVED_FOR_VERSION]->(v)
        RETURN part,
               COLLECT(DISTINCT {version: v.version, name: v.name, status: v.status}) AS versions,
               COLLECT(DISTINCT {name: mat.name, type: mat.material_type, spec: mat.specification}) AS materials,
               COLLECT(DISTINCT {name: geo.name, type: geo.model_type, units: geo.units}) AS geometry,
               COLLECT(DISTINCT asm.name) AS assemblies,
               COLLECT(DISTINCT req.name) AS requirements,
               COLLECT(DISTINCT appr.name) AS approvals
        """

        results = neo4j.execute_query(query, {"part_id": part_id})

        if not results or not results[0].get("part"):
            raise HTTPException(status_code=404, detail="Part not found")

        r = results[0]
        part = r["part"]

        part_detail = {
            "id": part.get("id"),
            "name": part.get("name", "Unknown"),
            "description": part.get("description"),
            "part_number": part.get("part_number"),
            "status": part.get("status"),
            "created_at": (
                str(part.get("created_at")) if part.get("created_at") else None
            ),
            "ap_level": part.get("ap_level"),
            "ap_schema": part.get("ap_schema"),
            "versions": [v for v in r["versions"] if v.get("version")],
            "materials": [m for m in r["materials"] if m.get("name")],
            "geometry": [g for g in r["geometry"] if g.get("name")],
            "assemblies": [a for a in r["assemblies"] if a],
            "requirements": [req for req in r["requirements"] if req],
            "approvals": [appr for appr in r["approvals"] if appr],
        }

        return part_detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching part {part_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/parts/{part_id}/bom", response_model=BOMResponse, response_class=Neo4jJSONResponse
)
async def get_part_bom(
    part_id: str = Path(..., description="Part ID"), api_key: str = Depends(get_api_key)
):
    """
    Get Bill of Materials (BOM) for a part

    Args:
        part_id: Unique part identifier

    Returns:
        Tree structure of assembly components
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (part:Part {id: $part_id})
        OPTIONAL MATCH (asm:Assembly)-[:ASSEMBLES_WITH]->(part)
        OPTIONAL MATCH (asm)-[:ASSEMBLES_WITH]->(subpart:Part)
        WHERE subpart.id <> $part_id
        RETURN part.name AS root_part,
               asm.name AS assembly,
               COLLECT(DISTINCT {
                   id: subpart.id,
                   name: subpart.name,
                   part_number: subpart.part_number
               }) AS components
        """

        results = neo4j.execute_query(query, {"part_id": part_id})

        if not results:
            raise HTTPException(status_code=404, detail="Part not found")

        return {
            "root_part": results[0]["root_part"],
            "assembly": results[0]["assembly"],
            "components": [c for c in results[0]["components"] if c.get("id")],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching BOM for {part_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ASSEMBLIES ENDPOINTS
# ============================================================================


@router.get(
    "/assemblies", response_model=AssembliesResponse, response_class=Neo4jJSONResponse
)
async def get_assemblies(
    type: Optional[str] = Query(
        None, description="Filter by assembly type (Mechanical, Electrical)"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get all assemblies

    Args:
        type: Filter by assembly type (Mechanical, Electrical, etc.)

    Returns:
        Array of assembly objects
    """
    try:
        neo4j = get_neo4j_service()

        where_clause = "asm.assembly_type = $type" if type else "1=1"
        params = {"type": type} if type else {}

        query = f"""
        MATCH (asm:Assembly)
        WHERE asm.ap_level = 2 AND {where_clause}
        OPTIONAL MATCH (asm)-[:ASSEMBLES_WITH]->(part:Part)
        RETURN asm.name AS name,
               asm.assembly_type AS type,
               asm.component_count AS component_count,
               COLLECT(DISTINCT part.name) AS parts
        ORDER BY asm.name
        """

        results = neo4j.execute_query(query, params)

        assemblies = [
            {
                "name": r["name"],
                "type": r["type"],
                "component_count": r["component_count"],
                "parts": [p for p in r["parts"] if p],
            }
            for r in results
        ]

        return {"count": len(assemblies), "assemblies": assemblies}

    except Exception as e:
        logger.error(f"Error fetching assemblies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MATERIALS ENDPOINTS
# ============================================================================


@router.get(
    "/materials", response_model=MaterialsResponse, response_class=Neo4jJSONResponse
)
async def get_materials(
    type: Optional[str] = Query(
        None, description="Filter by material type (Metal, Polymer, Composite)"
    ),
    search: Optional[str] = Query(None, description="Search in name and specification"),
    api_key: str = Depends(get_api_key),
):
    """
    Get all materials with optional filtering

    Args:
        type: Filter by material type (Metal, Polymer, Composite, etc.)
        search: Text search in name and specification

    Returns:
        Array of material objects
    """
    try:
        neo4j = get_neo4j_service()

        filters = []
        params = {}

        if type:
            filters.append("mat.material_type = $type")
            params["type"] = type

        if search:
            filters.append("(mat.name =~ $search OR mat.specification =~ $search)")
            params["search"] = f"(?i).*{search}.*"

        where_clause = " AND ".join(filters) if filters else "1=1"

        query = f"""
        MATCH (mat:Material)
        WHERE mat.ap_level = 2 AND {where_clause}
        OPTIONAL MATCH (mat)-[:HAS_PROPERTY]->(prop:MaterialProperty)
        OPTIONAL MATCH (part:Part)-[:USES_MATERIAL]->(mat)
        OPTIONAL MATCH (mat)-[:MATERIAL_CLASSIFIED_AS]->(owl:ExternalOwlClass)
        RETURN mat.name AS material_name,
               mat.material_type AS material_type,
               mat.specification AS material_specification,
               COLLECT(DISTINCT {{
                   prop_name: prop.name,
                   prop_value: prop.value,
                   prop_unit: prop.unit
               }}) AS properties,
               COLLECT(DISTINCT part.name) AS used_in_parts,
               COLLECT(DISTINCT owl.name) AS ontology_classes
        ORDER BY mat.name
        """

        results = neo4j.execute_query(query, params)

        materials = [
            {
                "name": r.get("material_name"),
                "type": r.get("material_type"),
                "specification": r.get("material_specification"),
                "properties": [
                    {
                        "name": p.get("prop_name"),
                        "value": p.get("prop_value"),
                        "unit": p.get("prop_unit"),
                    }
                    for p in r.get("properties", [])
                    if p and p.get("prop_name")
                ],
                "used_in_parts": [p for p in r.get("used_in_parts", []) if p],
                "ontology_classes": [o for o in r.get("ontology_classes", []) if o],
            }
            for r in results
            if r.get("material_name")
        ]

        return {"count": len(materials), "materials": materials}

    except Exception as e:
        logger.error(f"Error fetching materials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/materials/{material_name}",
    response_model=MaterialDetail,
    response_class=Neo4jJSONResponse,
)
async def get_material_detail(
    material_name: str = Path(..., description="Material name"),
    api_key: str = Depends(get_api_key),
):
    """
    Get detailed information about a specific material

    Args:
        material_name: Material name identifier

    Returns:
        Material with all properties and relationships
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (mat:Material {name: $material_name})
        OPTIONAL MATCH (mat)-[:HAS_PROPERTY]->(prop:MaterialProperty)
        OPTIONAL MATCH (prop)-[:USES_UNIT]->(unit:ExternalUnit)
        OPTIONAL MATCH (part:Part)-[:USES_MATERIAL]->(mat)
        OPTIONAL MATCH (mat)-[:MATERIAL_CLASSIFIED_AS]->(owl:ExternalOwlClass)
        OPTIONAL MATCH (req:Requirement)-[:REQUIRES_MATERIAL]->(mat)
        RETURN mat,
               COLLECT(DISTINCT {
                   name: prop.name,
                   value: prop.value,
                   unit: prop.unit,
                   temperature: prop.temperature,
                   unit_name: unit.name
               }) AS properties,
               COLLECT(DISTINCT part.name) AS parts,
               COLLECT(DISTINCT {name: owl.name, ontology: owl.ontology}) AS ontologies,
               COLLECT(DISTINCT req.name) AS requirements
        """

        results = neo4j.execute_query(query, {"material_name": material_name})

        if not results:
            raise HTTPException(status_code=404, detail="Material not found")

        r = results[0]
        mat = r["mat"]

        material_detail = {
            "name": mat["name"],
            "material_type": mat.get("material_type"),
            "specification": mat.get("specification"),
            "ap_level": mat.get("ap_level"),
            "ap_schema": mat.get("ap_schema"),
            "properties": [p for p in r["properties"] if p.get("name")],
            "used_in_parts": [p for p in r["parts"] if p],
            "ontology_classes": [o for o in r["ontologies"] if o.get("name")],
            "requirements": [req for req in r["requirements"] if req],
        }

        return material_detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching material {material_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GEOMETRY ENDPOINTS
# ============================================================================


@router.get(
    "/geometry", response_model=GeometryResponse, response_class=Neo4jJSONResponse
)
async def get_geometry_models(
    type: Optional[str] = Query(
        None, description="Filter by model type (Solid, Surface, Wireframe)"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get all CAD geometry models

    Args:
        type: Filter by model type (Solid, Surface, Wireframe)

    Returns:
        Array of geometric model objects
    """
    try:
        neo4j = get_neo4j_service()

        where_clause = "geo.model_type = $type" if type else "1=1"
        params = {"type": type} if type else {}

        query = f"""
        MATCH (geo:GeometricModel)
        WHERE geo.ap_level = 2 AND {where_clause}
        OPTIONAL MATCH (geo)-[:HAS_REPRESENTATION]->(shape:ShapeRepresentation)
        OPTIONAL MATCH (part:Part)-[:HAS_GEOMETRY]->(geo)
        OPTIONAL MATCH (ana:Analysis)-[:ANALYZES_GEOMETRY]->(geo)
        RETURN geo.name AS name,
               geo.model_type AS type,
               geo.units AS units,
               COLLECT(DISTINCT shape.representation_type) AS representations,
               COLLECT(DISTINCT part.name) AS parts,
               COLLECT(DISTINCT ana.name) AS analyses
        ORDER BY geo.name
        """

        results = neo4j.execute_query(query, params)

        geometry = [
            {
                "name": r["name"],
                "type": r["type"],
                "units": r["units"],
                "representations": [rep for rep in r["representations"] if rep],
                "parts": [p for p in r["parts"] if p],
                "analyses": [a for a in r["analyses"] if a],
            }
            for r in results
        ]

        return {"count": len(geometry), "geometry": geometry}

    except Exception as e:
        logger.error(f"Error fetching geometry models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATISTICS ENDPOINT
# ============================================================================


@router.get(
    "/statistics", response_model=StatisticsResponse, response_class=Neo4jJSONResponse
)
async def get_ap242_statistics(api_key: str = Depends(get_api_key)):
    """
    Get summary statistics for AP242 data

    Returns:
        Counts and type breakdown for all AP242 entities
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (n)
        WHERE n.ap_level = 2 AND n.ap_schema = 'AP242'
        WITH labels(n)[0] AS node_type, 
             COALESCE(n.status, n.material_type, n.assembly_type, n.model_type) AS type_or_status
        RETURN node_type, type_or_status, count(*) AS count
        ORDER BY node_type, type_or_status
        """

        results = neo4j.execute_query(query)

        # Group by node type
        stats = {}
        for r in results:
            node_type = r["node_type"]
            if node_type not in stats:
                stats[node_type] = {"total": 0, "breakdown": {}}
            stats[node_type]["total"] += r["count"]
            if r["type_or_status"]:
                stats[node_type]["breakdown"][r["type_or_status"]] = r["count"]

        return {"ap_level": 2, "ap_schema": "AP242", "statistics": stats}

    except Exception as e:
        logger.error(f"Error fetching AP242 statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
