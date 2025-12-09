"""
Simulation Integration Blueprint
Endpoints for simulation system integration:
- Parameter extraction
- Constraint validation
- Unit management
"""

from flask import Blueprint, jsonify, request
from loguru import logger

from src.web.middleware import DatabaseError, NotFoundError, ValidationError
from src.web.services import get_neo4j_service

simulation_bp = Blueprint("simulation", __name__, url_prefix="/api/v1/simulation")


@simulation_bp.route("/parameters", methods=["GET"])
def get_simulation_parameters():
    """
    Extract parameters for simulation with types, defaults, units, and constraints.
    Query params: class_name, property_name, data_type, include_constraints
    """
    service = get_neo4j_service()

    try:
        class_name = request.args.get("class_name")
        property_name = request.args.get("property_name")
        data_type = request.args.get("data_type")
        include_constraints = request.args.get("include_constraints", "true").lower() == "true"
        limit = request.args.get("limit", default=1000, type=int)

        if limit < 1 or limit > 5000:
            raise ValidationError("Limit must be between 1 and 5000")

        # Build query to extract properties with full simulation metadata
        query = """
        MATCH (p:Property)
        OPTIONAL MATCH (p)-[:TYPED_BY]->(type)
        OPTIONAL MATCH (owner)-[:HAS_ATTRIBUTE]->(p)
        OPTIONAL MATCH (p)-[r:HAS_RULE]->(constraint:Constraint)
        """

        # Add filters
        where_clauses = []
        params = {"limit": limit}

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
        RETURN p.id as id,
               p.name as name,
               p.type as property_type,
               type.name as data_type,
               type.id as type_id,
               p.visibility as visibility,
               p.lower as multiplicity_lower,
               p.upper as multiplicity_upper,
               p.default as default_value,
               p.defaultValue as default_value_alt,
               p.aggregation as aggregation,
               p.isDerived as is_derived,
               p.isReadOnly as is_read_only,
               owner.name as owner_class,
               owner.id as owner_id,
               COLLECT(DISTINCT {
                   id: constraint.id,
                   name: constraint.name,
                   body: constraint.body,
                   type: constraint.type
               }) as constraints
        ORDER BY owner.name, p.name
        LIMIT $limit
        """

        result = service.execute_query(query, params)

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

        return jsonify(
            {
                "total": len(parameters),
                "filters": {
                    "class_name": class_name,
                    "property_name": property_name,
                    "data_type": data_type,
                    "include_constraints": include_constraints,
                },
                "parameters": parameters,
            }
        )
    except ValidationError as e:
        raise
    except Exception as e:
        logger.error(f"Simulation parameters query error: {str(e)}")
        raise DatabaseError(f"Failed to retrieve simulation parameters: {str(e)}")


@simulation_bp.route("/validate", methods=["POST"])
def validate_simulation_parameters():
    """
    Validate parameter values against constraints.
    Body: { "parameters": [{"id": "prop_id", "value": 123}] }
    """
    service = get_neo4j_service()

    try:
        data = request.get_json()
        if not data or "parameters" not in data:
            raise ValidationError("Missing parameters in request body")

        parameters = data["parameters"]
        validation_results = []

        for param in parameters:
            param_id = param.get("id")
            param_value = param.get("value")

            if not param_id:
                validation_results.append({"valid": False, "error": "Missing parameter id"})
                continue

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

            result = service.execute_query(query, {"param_id": param_id})

            if not result:
                validation_results.append(
                    {"parameter_id": param_id, "valid": False, "error": "Parameter not found"}
                )
                continue

            record = result[0]
            violations = []

            # Check multiplicity constraints
            lower = record["lower"]
            upper = record["upper"]

            if lower is not None:
                if isinstance(param_value, list):
                    if len(param_value) < lower:
                        violations.append(
                            f"Value count {len(param_value)} is less than lower bound {lower}"
                        )
                elif lower > 0 and param_value is None:
                    violations.append(f"Value is required (lower bound: {lower})")

            if upper is not None and upper != -1:  # -1 means unlimited
                if isinstance(param_value, list) and len(param_value) > upper:
                    violations.append(f"Value count {len(param_value)} exceeds upper bound {upper}")

            # Check constraints (basic validation - can be extended)
            constraints = [c for c in record["constraints"] if c.get("id")]
            for constraint in constraints:
                body = constraint.get("body", "")
                # Simple constraint checks (extend for OCL parsing)
                if "not null" in body.lower() and param_value is None:
                    violations.append(f"Constraint violation: {constraint['name']} - {body}")

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

        return jsonify(
            {
                "total_parameters": len(validation_results),
                "valid_count": sum(1 for r in validation_results if r["valid"]),
                "invalid_count": sum(1 for r in validation_results if not r["valid"]),
                "results": validation_results,
            }
        )
    except ValidationError as e:
        raise
    except Exception as e:
        logger.error(f"Parameter validation error: {str(e)}")
        raise DatabaseError(f"Failed to validate parameters: {str(e)}")


@simulation_bp.route("/units", methods=["GET"])
def get_units():
    """
    Extract unit definitions from the model.
    Returns data types that represent units and their conversion factors if available.
    """
    service = get_neo4j_service()

    try:
        limit = request.args.get("limit", default=1000, type=int)

        if limit < 1 or limit > 5000:
            raise ValidationError("Limit must be between 1 and 5000")

        # Query for DataTypes and Enumerations that may represent units
        query = f"""
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

        result = service.execute_query(query, {"limit": limit})

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
        result = service.execute_query(unit_query)
        for record in result:
            unit_properties.append(
                {
                    "id": record["id"],
                    "name": record["name"],
                    "data_type": record["data_type"],
                    "owner_class": record["owner_class"],
                }
            )

        return jsonify(
            {
                "unit_types": {"total": len(units), "types": units},
                "unit_properties": {"total": len(unit_properties), "properties": unit_properties},
            }
        )
    except ValidationError as e:
        raise
    except Exception as e:
        logger.error(f"Units query error: {str(e)}")
        raise DatabaseError(f"Failed to retrieve units: {str(e)}")
