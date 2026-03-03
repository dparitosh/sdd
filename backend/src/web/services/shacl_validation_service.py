"""SHACL Validation Service — graph-level validation.

Validates nodes in the Neo4j knowledge graph against SHACL shape
definitions (``backend/data/seed/shacl/plmxml_shapes.ttl``) and persists
violations as ``:SHACLViolation`` nodes linked to the offending nodes.

This is distinct from the existing ``SHACLValidator`` which works on
uploaded RDF files.  This service queries Neo4j directly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from loguru import logger

from src.web.services import get_neo4j_service

# ---------------------------------------------------------------------------
# Shape definitions: which properties must exist for which labels
# ---------------------------------------------------------------------------

# Each shape is a dict:
#   label         — Neo4j node label to validate
#   shape_name    — short identifier
#   required_props — list of (prop_name, severity)  severity: violation | warning | info
#   numeric_min   — optional dict {prop: min_value} (exclusive)

_SHAPES: List[Dict[str, Any]] = [
    {
        "label": "PLMXMLItem",
        "shape_name": "PLMXMLItemShape",
        "required_props": [
            ("item_id", "violation"),
            ("name", "warning"),
        ],
        "numeric_min": {},
    },
    {
        "label": "PLMXMLRevision",
        "shape_name": "PLMXMLRevisionShape",
        "required_props": [
            ("revision", "violation"),
        ],
        "numeric_min": {},
    },
    {
        "label": "PLMXMLBOMLine",
        "shape_name": "PLMXMLBOMLineShape",
        "required_props": [
            ("ref_uid", "violation"),
        ],
        "numeric_min": {},
    },
    {
        "label": "PLMXMLDataSet",
        "shape_name": "PLMXMLDataSetShape",
        "required_props": [
            ("name", "violation"),
        ],
        "numeric_min": {},
    },
    {
        "label": "StepFile",
        "shape_name": "StepFileShape",
        "required_props": [],
        "numeric_min": {"entity_count": 0},
    },
]


# ---------------------------------------------------------------------------
# Cypher templates
# ---------------------------------------------------------------------------

_FIND_NODES = """
MATCH (n:{label})
RETURN n.uid AS uid, properties(n) AS props
"""

_FIND_SINGLE = """
MATCH (n {{uid: $uid}})
RETURN n.uid AS uid, labels(n) AS labels, properties(n) AS props
"""

_UPSERT_VIOLATION = """
MERGE (v:SHACLViolation {uid: $vid})
SET v.shape_name   = $shape_name,
    v.target_uid   = $target_uid,
    v.property     = $property,
    v.severity     = $severity,
    v.message      = $message,
    v.updated_at   = datetime()
WITH v
MATCH (n {uid: $target_uid})
MERGE (n)-[:HAS_VIOLATION]->(v)
"""

_DELETE_VIOLATIONS_FOR_NODE = """
MATCH (n {uid: $uid})-[:HAS_VIOLATION]->(v:SHACLViolation)
DETACH DELETE v
"""

_GET_VIOLATIONS_FOR_NODE = """
MATCH (n {uid: $uid})-[:HAS_VIOLATION]->(v:SHACLViolation)
RETURN v.uid          AS uid,
       v.shape_name   AS shape_name,
       v.property     AS property,
       v.severity     AS severity,
       v.message      AS message,
       v.updated_at   AS updated_at
ORDER BY v.severity, v.property
"""

_GET_VIOLATION_SUMMARY = """
MATCH (v:SHACLViolation)
RETURN v.shape_name AS shape_name,
       v.severity   AS severity,
       count(*)     AS count
ORDER BY shape_name, severity
"""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ViolationRecord:
    uid: str
    shape_name: str
    target_uid: str
    property: str
    severity: str
    message: str


@dataclass
class BatchValidationResult:
    label: str
    nodes_checked: int
    violations_found: int
    violations: List[ViolationRecord] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SHACLValidationService:
    """Validate Neo4j nodes against in-code shape definitions."""

    def __init__(self):
        self.neo4j = get_neo4j_service()

    # -- public API ----------------------------------------------------------

    def validate_node(self, uid: str) -> List[ViolationRecord]:
        """Validate a single node identified by *uid*.

        Clears previous violations for the node, then re-checks.
        """
        with self.neo4j.driver.session(database=self.neo4j.database) as session:
            # Find node and its labels
            result = session.run(_FIND_SINGLE, uid=uid)
            record = result.single()
            if record is None:
                logger.warning(f"SHACLValidation: node {uid} not found")
                return []

            labels = set(record["labels"])
            props = record["props"] or {}

            # Delete old violations
            session.run(_DELETE_VIOLATIONS_FOR_NODE, uid=uid)

            violations: List[ViolationRecord] = []
            for shape in _SHAPES:
                if shape["label"] in labels:
                    violations.extend(
                        self._check_shape(session, uid, props, shape)
                    )

        return violations

    def validate_batch(self, label: str) -> BatchValidationResult:
        """Validate all nodes with the given *label*.

        Returns aggregated results.
        """
        # Find the shape definition for this label
        shape = next((s for s in _SHAPES if s["label"] == label), None)
        if shape is None:
            logger.warning(f"SHACLValidation: no shape for label '{label}'")
            return BatchValidationResult(label=label, nodes_checked=0, violations_found=0)

        violations: List[ViolationRecord] = []
        nodes_checked = 0

        with self.neo4j.driver.session(database=self.neo4j.database) as session:
            cypher = _FIND_NODES.format(label=label)
            result = session.run(cypher)
            for record in result:
                uid = record["uid"]
                if uid is None:
                    continue
                props = record["props"] or {}
                nodes_checked += 1

                # Delete old violations for this node
                session.run(_DELETE_VIOLATIONS_FOR_NODE, uid=uid)

                violations.extend(
                    self._check_shape(session, uid, props, shape)
                )

        return BatchValidationResult(
            label=label,
            nodes_checked=nodes_checked,
            violations_found=len(violations),
            violations=violations,
        )

    def get_violations(self, uid: str) -> List[Dict[str, Any]]:
        """Query existing :SHACLViolation nodes linked to the node *uid*."""
        with self.neo4j.driver.session(database=self.neo4j.database) as session:
            result = session.run(_GET_VIOLATIONS_FOR_NODE, uid=uid)
            return [dict(r) for r in result]

    def get_report(self) -> List[Dict[str, Any]]:
        """Summary of all violations grouped by shape_name + severity."""
        with self.neo4j.driver.session(database=self.neo4j.database) as session:
            result = session.run(_GET_VIOLATION_SUMMARY)
            return [dict(r) for r in result]

    # -- internal ------------------------------------------------------------

    def _check_shape(
        self,
        session,
        uid: str,
        props: Dict[str, Any],
        shape: Dict[str, Any],
    ) -> List[ViolationRecord]:
        """Check a single node against a single shape definition."""
        violations: List[ViolationRecord] = []
        shape_name = shape["shape_name"]

        # Required-property checks
        for prop_name, severity in shape.get("required_props", []):
            val = props.get(prop_name)
            if val is None or (isinstance(val, str) and not val.strip()):
                v = ViolationRecord(
                    uid=str(uuid.uuid4()),
                    shape_name=shape_name,
                    target_uid=uid,
                    property=prop_name,
                    severity=severity,
                    message=f"Required property '{prop_name}' is missing or empty.",
                )
                violations.append(v)
                session.run(
                    _UPSERT_VIOLATION,
                    vid=v.uid,
                    shape_name=v.shape_name,
                    target_uid=v.target_uid,
                    property=v.property,
                    severity=v.severity,
                    message=v.message,
                )

        # Numeric-minimum checks
        for prop_name, min_val in shape.get("numeric_min", {}).items():
            val = props.get(prop_name)
            if val is None:
                v = ViolationRecord(
                    uid=str(uuid.uuid4()),
                    shape_name=shape_name,
                    target_uid=uid,
                    property=prop_name,
                    severity="violation",
                    message=f"Property '{prop_name}' is missing (must be > {min_val}).",
                )
                violations.append(v)
                session.run(
                    _UPSERT_VIOLATION,
                    vid=v.uid,
                    shape_name=v.shape_name,
                    target_uid=v.target_uid,
                    property=v.property,
                    severity=v.severity,
                    message=v.message,
                )
            elif isinstance(val, (int, float)) and val <= min_val:
                v = ViolationRecord(
                    uid=str(uuid.uuid4()),
                    shape_name=shape_name,
                    target_uid=uid,
                    property=prop_name,
                    severity="violation",
                    message=f"Property '{prop_name}' is {val}, must be > {min_val}.",
                )
                violations.append(v)
                session.run(
                    _UPSERT_VIOLATION,
                    vid=v.uid,
                    shape_name=v.shape_name,
                    target_uid=v.target_uid,
                    property=v.property,
                    severity=v.severity,
                    message=v.message,
                )

        return violations
