"""
Simulation Integration Routes (FastAPI)
Endpoints for simulation system integration:
- Parameter extraction with metadata
- Constraint validation
- Unit management and conversion
"""

from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field

from src.web.utils.responses import Neo4jJSONResponse
from src.web.services import get_neo4j_service

# ============================================================================
# ROUTER CONFIGURATION
# ============================================================================

router = APIRouter(prefix="/simulation", tags=["Simulation Integration"])


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

    This endpoint is intentionally tolerant: if no `SimulationResult` nodes exist,
    it returns an empty list.
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (r:SimulationResult)
        RETURN coalesce(r.id, r.uid, elementId(r)) as id,
               r.name as name,
               r.status as status,
               toString(r.created_on) as created_on,
               toString(r.last_modified) as last_modified,
               r.model_id as model_id,
               r.metrics as metrics,
               r.parameters as parameters
        ORDER BY coalesce(r.last_modified, r.created_on) DESC
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
