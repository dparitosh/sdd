"""
AP243 REST API Routes (FastAPI) - Reference Data and Ontologies
===============================================================
Endpoints for External Ontologies, Units, Value Types, and Classifications

ISO 10303 AP243 provides reference data integration with external ontologies
like EMMO, standardized units, value types, and classification systems.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Path
from pydantic import BaseModel, Field
from loguru import logger

from src.web.services import get_neo4j_service
from src.web.dependencies import get_api_key
from src.web.app_fastapi import Neo4jJSONResponse

router = APIRouter()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class OntologyClass(BaseModel):
    name: Optional[str] = "Unknown"
    ontology: Optional[str] = None
    uri: Optional[str] = None
    description: Optional[str] = None
    classified_materials: List[str] = []


class OntologiesResponse(BaseModel):
    count: int
    ontologies: List[OntologyClass]


class OntologyDetail(BaseModel):
    name: Optional[str] = "Unknown"
    ontology: Optional[str] = None
    uri: Optional[str] = None
    description: Optional[str] = None
    ap_level: Optional[int] = None
    ap_schema: Optional[str] = None
    classified_materials: List[str] = []
    related_parts: List[str] = []
    related_requirements: List[str] = []


class Unit(BaseModel):
    name: Optional[str] = "Unknown"
    symbol: Optional[str] = None
    type: Optional[str] = None
    si_conversion: Optional[Any] = None  # Can be string or float
    used_in_properties: List[str] = []
    used_in_requirements: List[str] = []


class UnitsResponse(BaseModel):
    count: int
    units: List[Unit]


class ValueType(BaseModel):
    name: str
    data_type: Optional[str] = None
    unit_reference: Optional[str] = None
    used_in_properties: List[str] = []


class ValueTypesResponse(BaseModel):
    count: int
    value_types: List[ValueType]


class Classification(BaseModel):
    name: str
    system: Optional[str] = None
    code: Optional[str] = None
    classified_parts: List[str] = []


class ClassificationsResponse(BaseModel):
    count: int
    classifications: List[Classification]


class StatisticsResponse(BaseModel):
    ap_level: int
    ap_schema: str
    statistics: Dict[str, int]


# ============================================================================
# ONTOLOGY ENDPOINTS
# ============================================================================


@router.get(
    "/ontologies", response_model=OntologiesResponse, response_class=Neo4jJSONResponse
)
async def get_ontologies(
    ontology: Optional[str] = Query(
        None, description="Filter by ontology name (EMMO, QUDT)"
    ),
    search: Optional[str] = Query(None, description="Search in name and description"),
    api_key: str = Depends(get_api_key),
):
    """
    Get all external ontology classes

    Args:
        ontology: Filter by ontology name (EMMO, QUDT, etc.)
        search: Text search in name and description

    Returns:
        Array of ontology class objects
    """
    try:
        neo4j = get_neo4j_service()

        filters = []
        params = {}

        if ontology:
            filters.append("owl.ontology = $ontology")
            params["ontology"] = ontology

        if search:
            filters.append("(owl.name =~ $search OR owl.description =~ $search)")
            params["search"] = f"(?i).*{search}.*"

        where_clause = " AND ".join(filters) if filters else "1=1"

        query = f"""
        MATCH (owl:ExternalOwlClass)
        WHERE owl.ap_level = 3 AND {where_clause}
        OPTIONAL MATCH (mat:Material)-[:MATERIAL_CLASSIFIED_AS]->(owl)
        RETURN owl.name AS name,
               owl.ontology AS ontology,
               owl.uri AS uri,
               owl.description AS description,
               COLLECT(DISTINCT mat.name) AS classified_materials
        ORDER BY owl.ontology, owl.name
        """

        results = neo4j.execute_query(query, params)

        ontologies = [
            {
                "name": r["name"] or "Unknown",
                "ontology": r["ontology"],
                "uri": r["uri"],
                "description": r["description"],
                "classified_materials": [m for m in r["classified_materials"] if m],
            }
            for r in results
        ]

        return {"count": len(ontologies), "ontologies": ontologies}

    except Exception as e:
        logger.error(f"Error fetching ontologies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/ontologies/{ontology_name}",
    response_model=OntologyDetail,
    response_class=Neo4jJSONResponse,
)
async def get_ontology_detail(
    ontology_name: str = Path(..., description="Ontology class name"),
    api_key: str = Depends(get_api_key),
):
    """
    Get detailed information about a specific ontology class

    Args:
        ontology_name: Name of the ontology class

    Returns:
        Ontology class with all relationships
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (owl:ExternalOwlClass {name: $ontology_name})
        OPTIONAL MATCH (mat:Material)-[:MATERIAL_CLASSIFIED_AS]->(owl)
        OPTIONAL MATCH (mat)<-[:USES_MATERIAL]-(part:Part)
        OPTIONAL MATCH (req:Requirement)-[:SATISFIED_BY_PART]->(part)
        RETURN owl,
               COLLECT(DISTINCT mat.name) AS materials,
               COLLECT(DISTINCT part.name) AS parts,
               COLLECT(DISTINCT req.name) AS requirements
        """

        results = neo4j.execute_query(query, {"ontology_name": ontology_name})

        if not results:
            raise HTTPException(status_code=404, detail="Ontology class not found")

        r = results[0]
        owl = r["owl"]

        ontology_detail = {
            "name": owl.get("name", "Unknown"),
            "ontology": owl.get("ontology"),
            "uri": owl.get("uri"),
            "description": owl.get("description"),
            "ap_level": owl.get("ap_level"),
            "ap_schema": owl.get("ap_schema"),
            "classified_materials": [m for m in r["materials"] if m],
            "related_parts": [p for p in r["parts"] if p],
            "related_requirements": [req for req in r["requirements"] if req],
        }

        return ontology_detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ontology {ontology_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# UNITS ENDPOINTS
# ============================================================================


@router.get("/units", response_model=UnitsResponse, response_class=Neo4jJSONResponse)
async def get_units(
    type: Optional[str] = Query(
        None, description="Filter by unit type (Temperature, ThermalConductivity)"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get all standardized units

    Args:
        type: Filter by unit type (Temperature, ThermalConductivity, etc.)

    Returns:
        Array of unit objects
    """
    try:
        neo4j = get_neo4j_service()

        where_clause = "unit.unit_type = $type" if type else "1=1"
        params = {"type": type} if type else {}

        query = f"""
        MATCH (unit:ExternalUnit)
        WHERE unit.ap_level = 3 AND {where_clause}
        OPTIONAL MATCH (prop:MaterialProperty)-[:USES_UNIT]->(unit)
        OPTIONAL MATCH (req:Requirement)-[:REQUIREMENT_VALUE_TYPE]->(unit)
        RETURN unit.name AS name,
               unit.symbol AS symbol,
               unit.unit_type AS type,
               unit.si_conversion AS si_conversion,
               COLLECT(DISTINCT prop.name) AS used_in_properties,
               COLLECT(DISTINCT req.name) AS used_in_requirements
        ORDER BY unit.unit_type, unit.name
        """

        results = neo4j.execute_query(query, params)

        units = [
            {
                "name": r["name"] or "Unknown",
                "symbol": r["symbol"],
                "type": r["type"],
                "si_conversion": r["si_conversion"],
                "used_in_properties": [p for p in r["used_in_properties"] if p],
                "used_in_requirements": [
                    req for req in r["used_in_requirements"] if req
                ],
            }
            for r in results
        ]

        return {"count": len(units), "units": units}

    except Exception as e:
        logger.error(f"Error fetching units: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# VALUE TYPES ENDPOINTS
# ============================================================================


@router.get(
    "/value-types", response_model=ValueTypesResponse, response_class=Neo4jJSONResponse
)
async def get_value_types(api_key: str = Depends(get_api_key)):
    """
    Get all value type definitions

    Returns:
        Array of value type objects
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (vt:ValueType)
        WHERE vt.ap_level = 3
        OPTIONAL MATCH (prop:MaterialProperty)-[:HAS_VALUE_TYPE]->(vt)
        RETURN vt.name AS name,
               vt.data_type AS data_type,
               vt.unit_reference AS unit_reference,
               COLLECT(DISTINCT prop.name) AS used_in_properties
        ORDER BY vt.name
        """

        results = neo4j.execute_query(query)

        value_types = [
            {
                "name": r["name"],
                "data_type": r["data_type"],
                "unit_reference": r["unit_reference"],
                "used_in_properties": [p for p in r["used_in_properties"] if p],
            }
            for r in results
        ]

        return {"count": len(value_types), "value_types": value_types}

    except Exception as e:
        logger.error(f"Error fetching value types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CLASSIFICATIONS ENDPOINTS
# ============================================================================


@router.get(
    "/classifications",
    response_model=ClassificationsResponse,
    response_class=Neo4jJSONResponse,
)
async def get_classifications(
    system: Optional[str] = Query(
        None, description="Filter by classification system (ISO 13584-501)"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get all classification systems

    Args:
        system: Filter by classification system (ISO 13584-501, etc.)

    Returns:
        Array of classification objects
    """
    try:
        neo4j = get_neo4j_service()

        where_clause = "class.classification_system = $system" if system else "1=1"
        params = {"system": system} if system else {}

        query = f"""
        MATCH (class:Classification)
        WHERE class.ap_level = 3 AND {where_clause}
        OPTIONAL MATCH (part:Part)-[:CLASSIFIED_AS]->(class)
        RETURN class.name AS name,
               class.classification_system AS system,
               class.code AS code,
               COLLECT(DISTINCT part.name) AS classified_parts
        ORDER BY class.classification_system, class.code
        """

        results = neo4j.execute_query(query, params)

        classifications = [
            {
                "name": r["name"],
                "system": r["system"],
                "code": r["code"],
                "classified_parts": [p for p in r["classified_parts"] if p],
            }
            for r in results
        ]

        return {"count": len(classifications), "classifications": classifications}

    except Exception as e:
        logger.error(f"Error fetching classifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATISTICS ENDPOINT
# ============================================================================


@router.get(
    "/statistics", response_model=StatisticsResponse, response_class=Neo4jJSONResponse
)
async def get_ap243_statistics(api_key: str = Depends(get_api_key)):
    """
    Get summary statistics for AP243 reference data

    Returns:
        Counts for all AP243 entities
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (n)
        WHERE n.ap_level = 3 AND n.ap_schema = 'AP243'
        WITH labels(n)[0] AS node_type
        RETURN node_type, count(*) AS count
        ORDER BY count DESC
        """

        results = neo4j.execute_query(query)

        stats = {r["node_type"]: r["count"] for r in results}

        return {"ap_level": 3, "ap_schema": "AP243", "statistics": stats}

    except Exception as e:
        logger.error(f"Error fetching AP243 statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
