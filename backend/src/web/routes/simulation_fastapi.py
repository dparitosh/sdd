"""
Simulation Integration Routes (FastAPI)
Endpoints for simulation system integration:
- Parameter extraction with metadata
- Constraint validation
- Unit management and conversion
"""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field

from src.web.utils.responses import Neo4jJSONResponse
from src.web.services import get_neo4j_service
from src.web.dependencies import get_api_key

# ============================================================================
# ROUTER CONFIGURATION
# ============================================================================

router = APIRouter(prefix="/simulation", tags=["Simulation Integration"], dependencies=[Depends(get_api_key)])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class Multiplicity(BaseModel):
    lower: Optional[str] = None
    upper: Optional[str] = None


class ParameterOwner(BaseModel):
    name: str
    id: str


class ParameterConstraint(BaseModel):
    id: str
    name: str
    body: Optional[str] = None
    type: Optional[str] = None


class SimulationParameter(BaseModel):
    id: str
    name: str
    property_type: Optional[str] = None
    data_type: Optional[str] = None
    type_id: Optional[str] = None
    visibility: Optional[str] = None
    multiplicity: Multiplicity
    default_value: Optional[Any] = None
    aggregation: Optional[str] = None
    is_derived: Optional[bool] = None
    is_read_only: Optional[bool] = None
    owner: Optional[ParameterOwner] = None
    constraints: Optional[List[ParameterConstraint]] = None


class SimulationParametersResponse(BaseModel):
    total: int
    filters: dict
    parameters: List[SimulationParameter]


class ParameterValueInput(BaseModel):
    id: str = Field(..., description="Parameter ID")
    value: Any = Field(..., description="Parameter value to validate")


class ValidationRequest(BaseModel):
    parameters: List[ParameterValueInput] = Field(
        ..., description="Parameters to validate"
    )


class ValidationResult(BaseModel):
    parameter_id: str
    parameter_name: Optional[str] = None
    value: Any
    valid: bool
    violations: List[str] = Field(default_factory=list)
    constraints_checked: int = 0


class ValidationResponse(BaseModel):
    total_parameters: int
    valid_count: int
    invalid_count: int
    results: List[ValidationResult]


class UnitType(BaseModel):
    id: str
    name: str
    type: Optional[str] = None
    labels: List[str]
    usage_count: int
    literals: Optional[List[str]] = None


class UnitProperty(BaseModel):
    id: str
    name: str
    data_type: Optional[str] = None
    owner_class: Optional[str] = None


class UnitTypesInfo(BaseModel):
    total: int
    types: List[UnitType]


class UnitPropertiesInfo(BaseModel):
    total: int
    properties: List[UnitProperty]


class UnitsResponse(BaseModel):
    unit_types: UnitTypesInfo
    unit_properties: UnitPropertiesInfo


class SimulationModelSummary(BaseModel):
    id: str
    name: str
    parameter_count: int
    constraint_count: int


class SimulationModelsResponse(BaseModel):
    total: int
    models: List[SimulationModelSummary]


class SimulationResultSummary(BaseModel):
    id: str
    name: Optional[str] = None
    status: Optional[str] = None
    created_on: Optional[str] = None
    last_modified: Optional[str] = None
    model_id: Optional[str] = None
    metrics: Optional[Any] = None
    parameters: Optional[Any] = None


class SimulationResultsResponse(BaseModel):
    total: int
    results: List[SimulationResultSummary]


# ============================================================================
# SIMULATION PARAMETERS ENDPOINT
# ============================================================================


@router.get(
    "/parameters",
    response_model=SimulationParametersResponse,
    response_class=Neo4jJSONResponse,
)
async def get_simulation_parameters(
    class_name: Optional[str] = Query(None, description="Filter by class name"),
    property_name: Optional[str] = Query(
        None, description="Filter by property name (pattern match)"
    ),
    data_type: Optional[str] = Query(None, description="Filter by data type"),
    include_constraints: bool = Query(
        True, description="Include constraint definitions"
    ),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of results"),
):
    """
    Extract parameters for simulation with types, defaults, units, and constraints

    Retrieves property metadata essential for simulation integration including:
    - Data types and multiplicity
    - Default values
    - Constraints for validation
    - Owner class information

    Args:
        class_name: Filter by owning class name
        property_name: Filter by property name (case-insensitive pattern)
        data_type: Filter by data type name
        include_constraints: Include constraint definitions
        limit: Maximum results (1-5000)

    Returns:
        List of simulation parameters with full metadata
    """
    try:
        neo4j = get_neo4j_service()

        # Build query to extract properties with full simulation metadata
        query = """
        MATCH (p:Property)
        OPTIONAL MATCH (p)-[:TYPED_BY]->(type)
        OPTIONAL MATCH (owner)-[:HAS_ATTRIBUTE]->(p)
        OPTIONAL MATCH (p)-[r:HAS_RULE]->(constraint:Constraint)
        """

        # Add filters
        where_clauses = []
        params: dict[str, Any] = {"limit": limit}

        if class_name:
            where_clauses.append("owner.name = $class_name")
            params["class_name"] = class_name

        if property_name:
            where_clauses.append("p.name =~ $property_pattern")
            params["property_pattern"] = f"(?i).*{property_name}.*"

        if data_type:
            where_clauses.append("type.name = $data_type")
            params["data_type"] = data_type

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += """
        RETURN coalesce(p.id, p.uid, elementId(p)) as id,
               p.name as name,
               p.type as property_type,
               type.name as data_type,
               coalesce(type.id, type.uid, (CASE WHEN type IS NULL THEN NULL ELSE elementId(type) END)) as type_id,
               p.visibility as visibility,
               toString(p.lower) as multiplicity_lower,
               toString(p.upper) as multiplicity_upper,
               p.default as default_value,
               p.defaultValue as default_value_alt,
               p.aggregation as aggregation,
               p.isDerived as is_derived,
               p.isReadOnly as is_read_only,
               owner.name as owner_class,
               coalesce(owner.id, owner.uid, (CASE WHEN owner IS NULL THEN NULL ELSE elementId(owner) END)) as owner_id,
               COLLECT(DISTINCT {
                   id: coalesce(constraint.id, constraint.uid, (CASE WHEN constraint IS NULL THEN NULL ELSE elementId(constraint) END)),
                   name: constraint.name,
                   body: constraint.body,
                   type: constraint.type
               }) as constraints
        ORDER BY owner.name, p.name
        LIMIT $limit
        """

        result = neo4j.execute_query(query, params)

        parameters = []
        for record in result:
            param = {
                "id": record["id"],
                "name": record["name"],
                "property_type": record["property_type"],
                "data_type": record["data_type"],
                "type_id": record["type_id"],
                "visibility": record["visibility"],
                "multiplicity": {
                    "lower": record["multiplicity_lower"],
                    "upper": record["multiplicity_upper"],
                },
                "default_value": record["default_value"] or record["default_value_alt"],
                "aggregation": record["aggregation"],
                "is_derived": record["is_derived"],
                "is_read_only": record["is_read_only"],
                "owner": (
                    {"name": record["owner_class"], "id": record["owner_id"]}
                    if record.get("owner_class")
                    else None
                ),
            }

            # Add constraints if requested
            if include_constraints:
                constraints = record["constraints"]
                param["constraints"] = [c for c in constraints if c.get("id")]

            parameters.append(param)

        return {
            "total": len(parameters),
            "filters": {
                "class_name": class_name,
                "property_name": property_name,
                "data_type": data_type,
                "include_constraints": include_constraints,
            },
            "parameters": parameters,
        }

    except Exception as e:
        logger.error(f"Simulation parameters query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve simulation parameters: {str(e)}",
        ) from e


# ============================================================================
# PARAMETER VALIDATION ENDPOINT
# ============================================================================


@router.post(
    "/validate", response_model=ValidationResponse, response_class=Neo4jJSONResponse
)
async def validate_simulation_parameters(validation_request: ValidationRequest):
    """
    Validate parameter values against constraints

    Checks parameter values against:
    - Multiplicity constraints (lower/upper bounds)
    - Custom constraints (basic validation)
    - Required value checks

    Args:
        validation_request: List of parameters with values to validate

    Returns:
        Validation results with violations for each parameter
    """
    try:
        neo4j = get_neo4j_service()

        if not validation_request.parameters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing parameters in request body",
            )

        parameters = validation_request.parameters
        validation_results = []

        for param in parameters:
            param_id = param.id
            param_value = param.value

            # Get constraints for this parameter
            query = """
            MATCH (p:Property {id: $param_id})
            OPTIONAL MATCH (p)-[:HAS_RULE]->(c:Constraint)
            RETURN p.id as id,
                   p.name as name,
                   p.lower as lower,
                   p.upper as upper,
                   COLLECT({
                       id: c.id,
                       name: c.name,
                       body: c.body
                   }) as constraints
            """

            result = neo4j.execute_query(query, {"param_id": param_id})

            if not result:
                validation_results.append(
                    {
                        "parameter_id": param_id,
                        "value": param_value,
                        "valid": False,
                        "violations": ["Parameter not found"],
                        "constraints_checked": 0,
                    }
                )
                continue

            record = result[0]
            violations = []

            # Check multiplicity constraints
            lower = record["lower"]
            upper = record["upper"]

            if lower is not None:
                lower_int = int(lower) if isinstance(lower, str) else lower
                if isinstance(param_value, list):
                    if len(param_value) < lower_int:
                        violations.append(
                            f"Value count {len(param_value)} is less than lower bound {lower_int}"
                        )
                elif lower_int > 0 and param_value is None:
                    violations.append(f"Value is required (lower bound: {lower_int})")

            if (
                upper is not None and upper != -1 and upper != "-1"
            ):  # -1 means unlimited
                upper_int = int(upper) if isinstance(upper, str) else upper
                if isinstance(param_value, list) and len(param_value) > upper_int:
                    violations.append(
                        f"Value count {len(param_value)} exceeds upper bound {upper_int}"
                    )

            # Check constraints (basic validation - can be extended)
            constraints = [c for c in record["constraints"] if c.get("id")]
            for constraint in constraints:
                body = constraint.get("body", "")
                # Simple constraint checks (extend for OCL parsing)
                if "not null" in body.lower() and param_value is None:
                    violations.append(
                        f"Constraint violation: {constraint['name']} - {body}"
                    )

            validation_results.append(
                {
                    "parameter_id": param_id,
                    "parameter_name": record["name"],
                    "value": param_value,
                    "valid": len(violations) == 0,
                    "violations": violations,
                    "constraints_checked": len(constraints),
                }
            )

        return {
            "total_parameters": len(validation_results),
            "valid_count": sum(1 for r in validation_results if r["valid"]),
            "invalid_count": sum(1 for r in validation_results if not r["valid"]),
            "results": validation_results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Parameter validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate parameters: {str(e)}",
        ) from e


# ============================================================================
# SIMULATION MODELS ENDPOINT
# ============================================================================


@router.get(
    "/models",
    response_model=SimulationModelsResponse,
    response_class=Neo4jJSONResponse,
)
async def get_simulation_models(
    limit: int = Query(200, ge=1, le=2000, description="Maximum number of results"),
):
    """List simulation model candidates derived from the graph.

    A "model" here is an owning Class that has Property nodes (simulation parameters).
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (c:Class)-[:HAS_ATTRIBUTE]->(p:Property)
        OPTIONAL MATCH (p)-[:HAS_RULE]->(constraint:Constraint)
        RETURN coalesce(c.id, c.uid, elementId(c)) as id,
               c.name as name,
               count(DISTINCT p) as parameter_count,
               count(DISTINCT constraint) as constraint_count
        ORDER BY c.name
        LIMIT $limit
        """

        rows = neo4j.execute_query(query, {"limit": limit})
        models = [
            {
                "id": r["id"],
                "name": r["name"],
                "parameter_count": int(r["parameter_count"] or 0),
                "constraint_count": int(r["constraint_count"] or 0),
            }
            for r in rows
            if r.get("id") and r.get("name")
        ]

        return {"total": len(models), "models": models}

    except Exception as e:
        logger.error(f"Simulation models query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve simulation models: {str(e)}",
        ) from e


# ============================================================================
# SIMULATION RESULTS ENDPOINT
# ============================================================================


@router.get(
    "/results",
    response_model=SimulationResultsResponse,
    response_class=Neo4jJSONResponse,
)
async def get_simulation_results(
    limit: int = Query(100, ge=1, le=2000, description="Maximum number of results"),
):
    """List stored simulation results (if present in the graph).

    This endpoint queries both `SimulationResult` and `SimulationArtifact` nodes,
    returning a unified list.  If neither label exists it returns an empty list.
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (r)
        WHERE r:SimulationResult OR r:SimulationArtifact
        RETURN coalesce(r.id, r.uid, elementId(r)) as id,
               r.name as name,
               r.status as status,
               toString(coalesce(r.created_on, r.created_at)) as created_on,
               toString(r.last_modified) as last_modified,
               coalesce(r.model_id, r.code) as model_id,
               r.metrics as metrics,
               r.type as parameters
        ORDER BY coalesce(r.last_modified, r.created_on, r.created_at) DESC
        LIMIT $limit
        """

        rows = neo4j.execute_query(query, {"limit": limit})
        results = [
            {
                "id": r["id"],
                "name": r.get("name"),
                "status": r.get("status"),
                "created_on": r.get("created_on"),
                "last_modified": r.get("last_modified"),
                "model_id": r.get("model_id"),
                "metrics": r.get("metrics"),
                "parameters": r.get("parameters"),
            }
            for r in rows
            if r.get("id")
        ]

        return {"total": len(results), "results": results}

    except Exception as e:
        logger.error(f"Simulation results query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve simulation results: {str(e)}",
        ) from e


# ============================================================================
# UNITS ENDPOINT
# ============================================================================


@router.get("/units", response_model=UnitsResponse, response_class=Neo4jJSONResponse)
async def get_units(
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of results")
):
    """
    Extract unit definitions from the model

    Returns data types that represent units and their conversion factors if available.
    Includes:
    - DataTypes, Enumerations, PrimitiveTypes
    - Properties with unit-related names
    - Usage counts for each unit type

    Args:
        limit: Maximum results (1-5000)

    Returns:
        Unit type definitions and unit-related properties
    """
    try:
        neo4j = get_neo4j_service()

        # Query for DataTypes and Enumerations that may represent units
        query = """
        MATCH (dt)
        WHERE dt:DataType OR dt:Enumeration OR dt:PrimitiveType
        OPTIONAL MATCH (dt)-[:HAS_LITERAL]->(lit:EnumerationLiteral)
        OPTIONAL MATCH (dt)<-[:TYPED_BY]-(prop:Property)
        RETURN dt.id as id,
               dt.name as name,
               dt.type as type,
               labels(dt) as labels,
               COLLECT(DISTINCT lit.name) as literals,
               COUNT(DISTINCT prop) as usage_count
        ORDER BY dt.name
        LIMIT $limit
        """

        result = neo4j.execute_query(query, {"limit": limit})

        units = []
        for record in result:
            unit = {
                "id": record["id"],
                "name": record["name"],
                "type": record["type"],
                "labels": record["labels"],
                "usage_count": record["usage_count"],
            }

            # Include literals for enumerations
            literals = record["literals"]
            if literals and any(literals):
                unit["literals"] = [lit for lit in literals if lit]

            units.append(unit)

        # Also query for properties with unit-related names
        unit_query = """
        MATCH (p:Property)
        WHERE p.name =~ '(?i).*(unit|dimension|quantity|measure).*'
        OPTIONAL MATCH (p)-[:TYPED_BY]->(type)
        OPTIONAL MATCH (owner)-[:HAS_ATTRIBUTE]->(p)
        RETURN p.id as id,
               p.name as name,
               type.name as data_type,
               owner.name as owner_class
        ORDER BY p.name
        LIMIT 50
        """

        unit_properties = []
        result = neo4j.execute_query(unit_query)
        for record in result:
            unit_properties.append(
                {
                    "id": record["id"],
                    "name": record["name"],
                    "data_type": record["data_type"],
                    "owner_class": record["owner_class"],
                }
            )

        return {
            "unit_types": {"total": len(units), "types": units},
            "unit_properties": {
                "total": len(unit_properties),
                "properties": unit_properties,
            },
        }

    except Exception as e:
        logger.error(f"Units query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve units: {str(e)}",
        ) from e


# ============================================================================
# SIMULATION DATA DOSSIER (SDD) ENDPOINTS
# ============================================================================
# Purpose: Manage simulation artifacts, dossiers, and MOSSEC traceability
# Created: February 24, 2026
# Related: docs/SDD_INTEGRATION_TRACKER.md
# ============================================================================


class DossierSummary(BaseModel):
    id: str
    name: str
    version: str
    status: str
    credibility_level: Optional[str] = None
    motor_id: Optional[str] = None
    project_name: Optional[str] = None
    engineer: Optional[str] = None
    last_updated: Optional[str] = None
    artifact_count: int = 0
    ap_level: Optional[str] = None
    ap_schema: Optional[str] = None


class DossiersListResponse(BaseModel):
    count: int
    dossiers: List[DossierSummary]
    limit: int
    offset: int


class ArtifactSummary(BaseModel):
    id: str
    name: str
    type: str
    status: str
    timestamp: Optional[str] = None
    size: Optional[str] = None
    checksum: Optional[str] = None
    requirement_id: Optional[str] = None
    requirement_name: Optional[str] = None
    ap_level: Optional[str] = None
    ap_schema: Optional[str] = None


class EvidenceCategory(BaseModel):
    id: str
    label: str
    status: str
    type: Optional[str] = None


class DossierDetail(BaseModel):
    id: str
    name: str
    version: str
    status: str
    credibility_level: Optional[str] = None
    motor_id: Optional[str] = None
    project_name: Optional[str] = None
    engineer: Optional[str] = None
    last_updated: Optional[str] = None
    ap_level: Optional[str] = None
    ap_schema: Optional[str] = None
    artifacts: List[dict] = Field(default_factory=list)
    evidence_categories: List[dict] = Field(default_factory=list)


class MOSSECTrace(BaseModel):
    requirement: Optional[dict] = None
    artifacts: List[dict] = Field(default_factory=list)
    trace_complete: bool = False


class CreateDossierInput(BaseModel):
    id: str = Field(..., description="Unique dossier ID (e.g., 'DOS-2024-006')")
    name: str = Field(..., description="Dossier name")
    version: str = Field(default="v1.0.0", description="Version string")
    status: str = Field(default="IN_PROGRESS", description="Dossier status")
    credibility_level: str = Field(default="PC3", description="Credibility level")
    motor_id: Optional[str] = Field(None, description="Motor ID")
    project_name: str = Field(..., description="Project name")
    engineer: str = Field(..., description="Engineer name")


class UpdateDossierInput(BaseModel):
    status: Optional[str] = None
    version: Optional[str] = None
    engineer: Optional[str] = None


@router.get(
    "/dossiers",
    response_model=DossiersListResponse,
    response_class=Neo4jJSONResponse,
    summary="List all simulation dossiers",
)
async def get_dossiers(
    dossier_status: Optional[str] = Query(None, description="Filter by status"),
    engineer: Optional[str] = Query(None, description="Filter by engineer"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip results"),
):
    """
    Get all simulation dossiers with optional filtering
    
    Returns list of dossiers with artifact counts and metadata.
    """
    try:
        from src.web.services.simulation_service import SimulationService
        
        neo4j = get_neo4j_service()
        sim_service = SimulationService(neo4j)
        
        result = sim_service.get_all_dossiers(
            status=dossier_status,
            engineer=engineer,
            limit=limit,
            offset=offset
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching dossiers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dossiers: {str(e)}"
        ) from e


@router.get(
    "/dossiers/{dossier_id}",
    response_model=DossierDetail,
    response_class=Neo4jJSONResponse,
    summary="Get dossier details",
)
async def get_dossier(dossier_id: str):
    """
    Get detailed dossier information including artifacts and evidence categories
    """
    try:
        from src.web.services.simulation_service import SimulationService
        
        neo4j = get_neo4j_service()
        sim_service = SimulationService(neo4j)
        
        result = sim_service.get_dossier_by_id(dossier_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dossier {dossier_id} not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching dossier {dossier_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dossier: {str(e)}"
        ) from e


@router.post(
    "/dossiers",
    response_model=dict,
    response_class=Neo4jJSONResponse,
    summary="Create new dossier",
    status_code=status.HTTP_201_CREATED,
)
async def create_dossier(dossier: CreateDossierInput):
    """
    Create a new simulation dossier
    """
    try:
        from src.web.services.simulation_service import SimulationService
        
        neo4j = get_neo4j_service()
        sim_service = SimulationService(neo4j)
        
        result = sim_service.create_dossier(dossier.model_dump())
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating dossier: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create dossier: {str(e)}"
        ) from e


@router.patch(
    "/dossiers/{dossier_id}",
    response_model=dict,
    response_class=Neo4jJSONResponse,
    summary="Update dossier",
)
async def update_dossier(dossier_id: str, updates: UpdateDossierInput):
    """
    Update dossier properties
    """
    try:
        from src.web.services.simulation_service import SimulationService
        
        neo4j = get_neo4j_service()
        sim_service = SimulationService(neo4j)
        
        # Only include non-None values
        update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid update fields provided"
            )
        
        result = sim_service.update_dossier(dossier_id, update_data)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dossier {dossier_id} not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating dossier {dossier_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update dossier: {str(e)}"
        ) from e


@router.get(
    "/artifacts",
    response_model=List[ArtifactSummary],
    response_class=Neo4jJSONResponse,
    summary="List simulation artifacts",
)
async def get_artifacts(
    dossier_id: Optional[str] = Query(None, description="Filter by dossier ID"),
    artifact_type: Optional[str] = Query(None, description="Filter by type"),
    artifact_status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    Get simulation artifacts with optional filtering
    """
    try:
        from src.web.services.simulation_service import SimulationService
        
        neo4j = get_neo4j_service()
        sim_service = SimulationService(neo4j)
        
        artifacts = sim_service.get_artifacts(
            dossier_id=dossier_id,
            artifact_type=artifact_type,
            status=artifact_status,
            limit=limit
        )
        
        return artifacts
        
    except Exception as e:
        logger.error(f"Error fetching artifacts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch artifacts: {str(e)}"
        ) from e


@router.get(
    "/artifacts/{artifact_id}",
    response_model=dict,
    response_class=Neo4jJSONResponse,
    summary="Get artifact details",
)
async def get_artifact(artifact_id: str):
    """
    Get detailed artifact information
    """
    try:
        from src.web.services.simulation_service import SimulationService
        
        neo4j = get_neo4j_service()
        sim_service = SimulationService(neo4j)
        
        result = sim_service.get_artifact_by_id(artifact_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact {artifact_id} not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching artifact {artifact_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch artifact: {str(e)}"
        ) from e


@router.get(
    "/trace/{requirement_id}",
    response_model=MOSSECTrace,
    response_class=Neo4jJSONResponse,
    summary="Get MOSSEC traceability",
)
async def get_mossec_trace(
    requirement_id: str,
    max_depth: int = Query(7, ge=1, le=10, description="Maximum trace depth"),
):
    """
    Get full MOSSEC traceability chain from requirement to approval
    """
    try:
        from src.web.services.simulation_service import SimulationService
        
        neo4j = get_neo4j_service()
        sim_service = SimulationService(neo4j)
        
        trace = sim_service.get_mossec_trace(requirement_id, max_depth)
        
        return trace
        
    except Exception as e:
        logger.error(f"Error fetching MOSSEC trace for {requirement_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch MOSSEC trace: {str(e)}"
        ) from e


@router.get(
    "/statistics",
    response_model=dict,
    response_class=Neo4jJSONResponse,
    summary="Get simulation statistics",
)
async def get_simulation_statistics():
    """
    Get simulation data statistics (counts, status distribution)
    """
    try:
        from src.web.services.simulation_service import SimulationService
        
        neo4j = get_neo4j_service()
        sim_service = SimulationService(neo4j)
        
        stats = sim_service.get_statistics()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch statistics: {str(e)}"
        ) from e


# ============================================================================
# SIMULATION RUN ENDPOINTS (Sprint 2)
# ============================================================================

class SimulationRunSummary(BaseModel):
    """Summary of a simulation run"""
    id: str
    sim_type: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str
    solver_version: Optional[str] = None
    credibility_level: Optional[str] = None
    mesh_elements: Optional[int] = None
    cpu_hours: Optional[float] = None
    generated_artifacts: List[str] = Field(default_factory=list)
    ap_level: Optional[str] = None


class SimulationRunDetail(BaseModel):
    """Detailed simulation run information"""
    id: str
    sim_type: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    timestamp: Optional[str] = None
    status: str
    solver_version: Optional[str] = None
    credibility_level: Optional[str] = None
    mesh_elements: Optional[int] = None
    convergence_tolerance: Optional[float] = None
    cpu_hours: Optional[float] = None
    dossier_id: Optional[str] = None
    dossier_name: Optional[str] = None
    generated_artifacts: List[dict] = Field(default_factory=list)
    ap_level: Optional[str] = None
    ap_schema: Optional[str] = None


class CreateSimulationRunInput(BaseModel):
    """Input for creating a new simulation run"""
    id: str = Field(..., description="Unique run ID (e.g., 'SR-2024-004')")
    sim_type: str = Field(..., description="Simulation type (Electromagnetic, Thermal, NVH, etc.)")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    start_time: Optional[str] = Field(None, description="Start time (defaults to timestamp)")
    end_time: Optional[str] = Field(None, description="End time for completed runs")
    run_status: Optional[str] = Field("Running", description="Run status (Running, Complete, Failed)")
    solver_version: Optional[str] = Field(None, description="Solver version")
    credibility_level: Optional[str] = Field("PC2", description="MOSSEC credibility level")
    mesh_elements: Optional[int] = None
    convergence_tolerance: Optional[float] = None
    cpu_hours: Optional[float] = Field(None, description="CPU hours consumed")
    dossier_id: Optional[str] = Field(None, description="Parent dossier ID")


@router.get(
    "/runs",
    response_model=List[SimulationRunSummary],
    response_class=Neo4jJSONResponse,
    summary="List simulation runs",
)
async def get_simulation_runs(
    dossier_id: Optional[str] = Query(None, description="Filter by dossier ID"),
    run_status: Optional[str] = Query(None, description="Filter by status"),
    sim_type: Optional[str] = Query(None, description="Filter by simulation type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
):
    """
    Get all simulation runs with optional filtering
    """
    try:
        from src.web.services.simulation_service import SimulationService
        
        neo4j = get_neo4j_service()
        sim_service = SimulationService(neo4j)
        
        runs = sim_service.get_simulation_runs(
            dossier_id=dossier_id,
            status=run_status,
            sim_type=sim_type,
            limit=limit
        )
        
        # Convert Neo4j temporal types to ISO strings
        for run in runs:
            for key in ('timestamp', 'start_time', 'end_time'):
                val = run.get(key)
                if val is not None and not isinstance(val, str):
                    run[key] = str(val)
        
        return runs
        
    except Exception as e:
        logger.error(f"Error fetching simulation runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch simulation runs: {str(e)}"
        ) from e


@router.get(
    "/runs/{run_id}",
    response_model=SimulationRunDetail,
    response_class=Neo4jJSONResponse,
    summary="Get simulation run details",
)
async def get_simulation_run(run_id: str):
    """
    Get detailed simulation run information including generated artifacts
    """
    try:
        from src.web.services.simulation_service import SimulationService
        
        neo4j = get_neo4j_service()
        sim_service = SimulationService(neo4j)
        
        run = sim_service.get_simulation_run_by_id(run_id)
        
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Simulation run '{run_id}' not found"
            )
        
        # Convert Neo4j temporal types to ISO strings
        for key in ('timestamp', 'start_time', 'end_time'):
            val = run.get(key)
            if val is not None and not isinstance(val, str):
                run[key] = str(val)
        
        return run
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching simulation run {run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch simulation run: {str(e)}"
        ) from e


@router.post(
    "/runs",
    response_model=dict,
    response_class=Neo4jJSONResponse,
    summary="Create simulation run",
    status_code=status.HTTP_201_CREATED,
)
async def create_simulation_run(run_input: CreateSimulationRunInput):
    """
    Create a new simulation run and optionally link to a dossier
    """
    try:
        from src.web.services.simulation_service import SimulationService
        
        neo4j = get_neo4j_service()
        sim_service = SimulationService(neo4j)
        
        # Convert run_input to dict and rename run_status -> status for service layer
        run_data = run_input.dict()
        if 'run_status' in run_data:
            run_data['status'] = run_data.pop('run_status')
        
        run = sim_service.create_simulation_run(run_data)
        
        return run
        
    except Exception as e:
        logger.error(f"Error creating simulation run: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create simulation run: {str(e)}"
        ) from e


# ============================================================================
# DOSSIER AUDIT ENDPOINTS (ISO-CASCO Compliance)
# ============================================================================
# These proxy to the AuditService in src/functions/audit_service
# so the frontend can reach audit via /api/simulation/dossiers/{id}/audit
# ============================================================================


@router.post(
    "/dossiers/{dossier_id}/audit",
    response_class=Neo4jJSONResponse,
    summary="Run compliance audit on a dossier",
)
async def run_dossier_audit(dossier_id: str):
    """
    Run ISO-CASCO compliance audit on a dossier.
    Returns audit report with health score and findings.
    """
    try:
        from src.functions.audit_service.service import AuditService

        svc = AuditService()
        report = svc.run_audit(dossier_id)
        # AuditReport is a Pydantic model — convert to dict
        return report.model_dump() if hasattr(report, "model_dump") else report
    except Exception as exc:
        logger.error(f"Audit failed for dossier {dossier_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/dossiers/{dossier_id}/audit",
    response_class=Neo4jJSONResponse,
    summary="Get audit findings for a dossier",
)
async def get_dossier_audit(dossier_id: str):
    """
    Retrieve the latest audit findings for a dossier.
    Runs a fresh audit and returns the findings array.
    """
    try:
        from src.functions.audit_service.service import AuditService

        svc = AuditService()
        report = svc.run_audit(dossier_id)
        data = report.model_dump() if hasattr(report, "model_dump") else report
        return {"findings": data.get("findings", [])}
    except Exception as exc:
        logger.error(f"Audit findings fetch failed for dossier {dossier_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ============================================================================
# DOSSIER APPROVAL ENDPOINTS (Quality Head Sign-off)
# ============================================================================
# These proxy to the ApprovalService in src/functions/approval_service
# ============================================================================


class ApproveInput(BaseModel):
    """Approval decision body — maps to ApprovalService.approve()."""
    status: str = Field(..., description="'Approved' or 'Rejected'")
    reviewer: str = Field(..., description="Name of the reviewer")
    comment: str = Field(default="", description="Rationale / comment")
    signature_id: Optional[str] = Field(None, description="Digital signature ID")
    role: str = Field(default="", description="Reviewer role")


@router.post(
    "/dossiers/{dossier_id}/approve",
    response_class=Neo4jJSONResponse,
    summary="Submit approval decision for a dossier",
)
async def approve_dossier(dossier_id: str, body: ApproveInput):
    """
    Submit an approval or rejection decision for a dossier.
    Creates an immutable ApprovalRecord and updates dossier status.
    """
    try:
        from src.functions.approval_service.service import ApprovalService

        svc = ApprovalService()
        record = svc.approve(
            dossier_id=dossier_id,
            status=body.status,
            reviewer=body.reviewer,
            comment=body.comment,
            signature_id=body.signature_id,
            role=body.role,
        )
        return record.model_dump() if hasattr(record, "model_dump") else record
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Approval failed for dossier {dossier_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/dossiers/{dossier_id}/approvals",
    response_class=Neo4jJSONResponse,
    summary="Get approval history for a dossier",
)
async def get_approval_history(dossier_id: str):
    """
    Return all decision-log entries for a dossier, ordered by timestamp.
    """
    try:
        from src.functions.approval_service.service import ApprovalService

        svc = ApprovalService()
        history = svc.get_history(dossier_id)
        items = [h.model_dump() if hasattr(h, "model_dump") else h for h in history]
        return {"history": items}
    except Exception as exc:
        logger.error(f"Approval history fetch failed for dossier {dossier_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ============================================================================
# WORKFLOW ROUTES  (STEP AP243: WorkflowMethod / TaskElement)
# ============================================================================

@router.get(
    "/workflows",
    response_class=Neo4jJSONResponse,
    summary="List all simulation workflows (WorkflowMethod nodes)",
)
async def get_workflows(
    sim_type: Optional[str] = Query(None, description="Filter by simulation type"),
    status:   Optional[str] = Query(None, description="Filter by status"),
    limit:    int            = Query(50, description="Max results"),
):
    """
    Returns a list of WorkflowMethod nodes representing reusable simulation
    procedures, following ISO 10303-41 action_method and Part 49
    method_definition_schema patterns.
    """
    try:
        from src.web.services.simulation_service import SimulationService
        sim_svc = SimulationService(get_neo4j_service())
        workflows = sim_svc.get_workflows(sim_type=sim_type, status=status, limit=limit)
        return {"total": len(workflows), "workflows": workflows}
    except Exception as exc:
        logger.error(f"Error fetching workflows: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/workflows/{workflow_id}",
    response_class=Neo4jJSONResponse,
    summary="Get a single WorkflowMethod with ordered TaskElement steps",
)
async def get_workflow(workflow_id: str):
    """
    Returns a WorkflowMethod with:
    - Ordered TaskElement step chain (sequential_method pattern)
    - ActionResource list (solver, compute)
    - Linked SimulationRun instances
    """
    try:
        from src.web.services.simulation_service import SimulationService
        sim_svc = SimulationService(get_neo4j_service())
        wf = sim_svc.get_workflow_by_id(workflow_id)
        if not wf:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
        return wf
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching workflow {workflow_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/workflows/{workflow_id}/graph",
    response_class=Neo4jJSONResponse,
    summary="Get graph nodes+edges for a WorkflowMethod (for visualisation)",
)
async def get_workflow_graph(workflow_id: str):
    """
    Returns a graph payload (nodes + edges) covering:
      WorkflowMethod, TaskElement, ActionResource, SimulationRun
    with relationship types: HAS_STEP, NEXT_STEP, USES_RESOURCE, CHOSEN_METHOD
    """
    try:
        from src.web.services.simulation_service import SimulationService
        sim_svc = SimulationService(get_neo4j_service())
        graph = sim_svc.get_workflow_graph(workflow_id)
        return graph
    except Exception as exc:
        logger.error(f"Error fetching workflow graph {workflow_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc