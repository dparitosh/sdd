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
from src.web.utils.responses import Neo4jJSONResponse

router = APIRouter()

# MoSSEC-specific node labels (AP243 XMI model + reference data)
MOSSEC_LABELS = [
    "Class", "Property", "Port", "Connector", "Association",
    "Generalization", "Package", "Constraint", "InstanceSpecification",
    "Comment", "ExternalOwlClass", "ExternalOntology",
]

# MoSSEC-specific relationship types
MOSSEC_REL_TYPES = [
    "CONTAINS", "OWNS", "DEFINES", "ASSOCIATES_WITH", "HAS_ATTRIBUTE",
    "TYPED_BY", "GENERALIZES_TO", "HAS_PORT", "DEFINES_REFERENCE_DATA",
    "SUBCLASS_OF",
]


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


class DomainClass(BaseModel):
    name: Optional[str] = "Unknown"
    xmi_id: Optional[str] = None
    xmi_type: Optional[str] = None
    stereotype: Optional[str] = None
    is_abstract: Optional[bool] = None
    visibility: Optional[str] = None
    source_file: Optional[str] = None
    properties: List[str] = []
    ports: List[str] = []
    generalizations: List[str] = []


class DomainClassesResponse(BaseModel):
    count: int
    classes: List[DomainClass]


class AP243OverviewResponse(BaseModel):
    total_nodes: int
    total_relationships: int
    node_types: Dict[str, int]
    relationship_types: Dict[str, int]
    domain_packages: List[str]


class DomainSearchResult(BaseModel):
    name: Optional[str] = None
    label: Optional[str] = None
    id: Optional[str] = None
    properties: Dict[str, Any] = {}


class DomainSearchResponse(BaseModel):
    count: int
    results: List[DomainSearchResult]


# ============================================================================
# AP243 OVERVIEW & DOMAIN ENDPOINTS
# ============================================================================


@router.get("/overview", response_class=Neo4jJSONResponse)
async def get_ap243_overview(api_key: str = Depends(get_api_key)):
    """
    Get a high-level overview of all AP243/MoSSEC data in the graph.
    Returns total counts per node type and relationship type.
    """
    try:
        neo4j = get_neo4j_service()

        node_query = """
        MATCH (n)
        WHERE any(lbl IN labels(n) WHERE lbl IN $labels)
        RETURN labels(n)[0] AS label, count(*) AS cnt
        ORDER BY cnt DESC
        """
        rel_query = """
        MATCH ()-[r]->()
        WHERE type(r) IN $rel_types
        RETURN type(r) AS rel, count(*) AS cnt
        ORDER BY cnt DESC
        """
        pkg_query = """
        MATCH (p:Package)
        RETURN p.name AS name
        ORDER BY p.name
        """

        nodes = neo4j.execute_query(node_query, {"labels": MOSSEC_LABELS})
        rels = neo4j.execute_query(rel_query, {"rel_types": MOSSEC_REL_TYPES})
        pkgs = neo4j.execute_query(pkg_query)

        node_types = {r["label"]: r["cnt"] for r in nodes if r["label"]}
        rel_types = {r["rel"]: r["cnt"] for r in rels if r["rel"]}
        packages = [r["name"] for r in pkgs if r["name"]]

        return {
            "total_nodes": sum(node_types.values()),
            "total_relationships": sum(rel_types.values()),
            "node_types": node_types,
            "relationship_types": rel_types,
            "domain_packages": packages,
        }
    except Exception as e:
        logger.error(f"Error fetching AP243 overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domain-classes", response_model=DomainClassesResponse, response_class=Neo4jJSONResponse)
async def get_domain_classes(
    search: Optional[str] = Query(None, description="Search in class name"),
    stereotype: Optional[str] = Query(None, description="Filter by stereotype"),
    is_abstract: Optional[bool] = Query(None, description="Filter by abstract flag"),
    package: Optional[str] = Query(None, description="Filter by package name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    api_key: str = Depends(get_api_key),
):
    """
    Get AP243/MoSSEC domain classes from the XMI model.
    These are the core type definitions of the MoSSEC standard.
    """
    try:
        neo4j = get_neo4j_service()

        filters = []
        params: Dict[str, Any] = {"skip": skip, "limit": limit}

        if search:
            filters.append("c.name =~ $search")
            params["search"] = f"(?i).*{search}.*"
        if stereotype:
            filters.append("c.stereotype = $stereotype")
            params["stereotype"] = stereotype
        if is_abstract is not None:
            filters.append("c.is_abstract = $is_abstract")
            params["is_abstract"] = is_abstract
        if package:
            filters.append("EXISTS { MATCH (pkg:Package {name: $package})-[:CONTAINS*]->(c) }")
            params["package"] = package

        where = " AND ".join(filters) if filters else "1=1"

        query = f"""
        MATCH (c:Class)
        WHERE {where}
        OPTIONAL MATCH (c)<-[:TYPED_BY]-(prop:Property)
        OPTIONAL MATCH (c)<-[:HAS_PORT]-(port:Port)
        OPTIONAL MATCH (c)-[:GENERALIZES_TO]->(parent:Class)
        RETURN c.name AS name,
               c.xmi_id AS xmi_id,
               c.xmi_type AS xmi_type,
               c.stereotype AS stereotype,
               c.is_abstract AS is_abstract,
               c.visibility AS visibility,
               c.source_file AS source_file,
               COLLECT(DISTINCT prop.name) AS properties,
               COLLECT(DISTINCT port.name) AS ports,
               COLLECT(DISTINCT parent.name) AS generalizations
        ORDER BY c.name
        SKIP $skip LIMIT $limit
        """

        results = neo4j.execute_query(query, params)

        classes = [
            {
                "name": r["name"] or "Unknown",
                "xmi_id": r["xmi_id"],
                "xmi_type": r["xmi_type"],
                "stereotype": r["stereotype"],
                "is_abstract": r["is_abstract"],
                "visibility": r["visibility"],
                "source_file": r["source_file"],
                "properties": [p for p in r["properties"] if p],
                "ports": [p for p in r["ports"] if p],
                "generalizations": [g for g in r["generalizations"] if g],
            }
            for r in results
        ]

        return {"count": len(classes), "classes": classes}
    except Exception as e:
        logger.error(f"Error fetching domain classes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domain-classes/{class_name}", response_class=Neo4jJSONResponse)
async def get_domain_class_detail(
    class_name: str = Path(..., description="Class name"),
    api_key: str = Depends(get_api_key),
):
    """
    Get detailed information about a specific MoSSEC domain class,
    including its properties, ports, connectors, and relationships.
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (c:Class {name: $name})
        OPTIONAL MATCH (c)<-[:TYPED_BY]-(prop:Property)
        OPTIONAL MATCH (c)<-[:HAS_PORT]-(port:Port)
        OPTIONAL MATCH (c)<-[:OWNS]-(owner)
        OPTIONAL MATCH (c)-[:GENERALIZES_TO]->(parent:Class)
        OPTIONAL MATCH (child:Class)-[:GENERALIZES_TO]->(c)
        OPTIONAL MATCH (c)<-[:ASSOCIATES_WITH]-(assoc:Association)
        OPTIONAL MATCH (c)<-[:DEFINES]-(connector:Connector)
        RETURN c,
               COLLECT(DISTINCT {name: prop.name, type: prop.xmi_type, aggregation: prop.aggregation}) AS properties,
               COLLECT(DISTINCT {name: port.name, direction: port.direction}) AS ports,
               COLLECT(DISTINCT owner.name) AS owned_by,
               COLLECT(DISTINCT parent.name) AS parents,
               COLLECT(DISTINCT child.name) AS children,
               COLLECT(DISTINCT assoc.name) AS associations,
               COLLECT(DISTINCT connector.name) AS connectors
        """

        results = neo4j.execute_query(query, {"name": class_name})

        if not results:
            raise HTTPException(status_code=404, detail=f"Class '{class_name}' not found")

        r = results[0]
        node = r["c"]

        return {
            "name": node.get("name"),
            "xmi_id": node.get("xmi_id"),
            "xmi_type": node.get("xmi_type"),
            "stereotype": node.get("stereotype"),
            "is_abstract": node.get("is_abstract"),
            "visibility": node.get("visibility"),
            "source_file": node.get("source_file"),
            "properties": [p for p in r["properties"] if p.get("name")],
            "ports": [p for p in r["ports"] if p.get("name")],
            "owned_by": [o for o in r["owned_by"] if o],
            "parents": [p for p in r["parents"] if p],
            "children": [ch for ch in r["children"] if ch],
            "associations": [a for a in r["associations"] if a],
            "connectors": [c for c in r["connectors"] if c],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching class {class_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domain-search", response_model=DomainSearchResponse, response_class=Neo4jJSONResponse)
async def domain_search(
    q: str = Query(..., description="Search query"),
    node_type: Optional[str] = Query(None, description="Filter by node label (Class, Property, Port, etc.)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    api_key: str = Depends(get_api_key),
):
    """
    Full-text search across all AP243/MoSSEC domain entities.
    Searches name, xmi_id, stereotype, and comment fields.
    """
    try:
        neo4j = get_neo4j_service()

        # Validate node_type against known labels to prevent Cypher injection
        if node_type and node_type not in MOSSEC_LABELS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid node_type: {node_type}. Must be one of: {', '.join(MOSSEC_LABELS)}"
            )

        label_filter = f":{node_type}" if node_type else ""
        params: Dict[str, Any] = {
            "q": f"(?i).*{q}.*",
            "skip": skip,
            "limit": limit,
            "labels": MOSSEC_LABELS,
        }

        query = f"""
        MATCH (n{label_filter})
        WHERE any(lbl IN labels(n) WHERE lbl IN $labels)
          AND (n.name =~ $q
           OR (n.comment IS NOT NULL AND n.comment =~ $q)
           OR (n.stereotype IS NOT NULL AND n.stereotype =~ $q))
        RETURN labels(n)[0] AS label,
               n.name AS name,
               n.id AS id,
               properties(n) AS props
        ORDER BY n.name
        SKIP $skip LIMIT $limit
        """

        results = neo4j.execute_query(query, params)

        items = [
            {
                "label": r["label"],
                "name": r["name"],
                "id": r["id"],
                "properties": {k: v for k, v in (r["props"] or {}).items()
                               if k not in ("name", "id") and v is not None},
            }
            for r in results
        ]

        return {"count": len(items), "results": items}
    except Exception as e:
        logger.error(f"Error in domain search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/packages", response_class=Neo4jJSONResponse)
async def get_packages(api_key: str = Depends(get_api_key)):
    """
    List all MoSSEC packages with their contained class counts.
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (p:Package)
        OPTIONAL MATCH (p)-[:CONTAINS]->(c:Class)
        RETURN p.name AS name,
               p.id AS id,
               count(c) AS class_count
        ORDER BY p.name
        """

        results = neo4j.execute_query(query)

        return {
            "count": len(results),
            "packages": [
                {"name": r["name"], "id": r["id"], "class_count": r["class_count"]}
                for r in results
            ],
        }
    except Exception as e:
        logger.error(f"Error fetching packages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stereotypes", response_class=Neo4jJSONResponse)
async def get_stereotypes(api_key: str = Depends(get_api_key)):
    """
    List all distinct stereotypes in the MoSSEC model.
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (c:Class)
        WHERE c.stereotype IS NOT NULL
        RETURN c.stereotype AS stereotype, count(*) AS count
        ORDER BY count DESC
        """

        results = neo4j.execute_query(query)

        return {
            "count": len(results),
            "stereotypes": [{"name": r["stereotype"], "count": r["count"]} for r in results],
        }
    except Exception as e:
        logger.error(f"Error fetching stereotypes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
