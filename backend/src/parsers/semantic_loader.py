"""
Semantic XMI to Neo4j loader based on OMG UML/SysML metamodel principles.
Distinguishes between first-class model elements (nodes), relationships, and metadata (properties).
"""

from pathlib import Path
from typing import Dict, List, Set, Tuple

from loguru import logger
from lxml import etree

from src.graph.connection import Neo4jConnection


class SemanticXMILoader:
    """
    Load XMI files into Neo4j following OMG UML/SysML metamodel semantics.

    Design Principles:
    - NODES: First-class model elements with identity (Package, Class, Property, Port, etc.)
    - RELATIONSHIPS: Semantic connections (Association, Generalization, Connector, etc.)
    - PROPERTIES: Metadata stored as node attributes (Comments, Literals, etc.)
    - CONTAINMENT: Hierarchical relationships (CONTAINS, HAS_ATTRIBUTE, HAS_OPERATION)
    - COMPLETE UML/SysML METAMODEL: All standardized elements with full properties
    - PLM INTEGRATION: Version tracking, traceability, change management
    """

    # Elements that should be created as NODES (first-class elements with identity)
    # Complete UML 2.5.1 + SysML 1.6 + AP239/AP242/AP243 coverage
    NODE_TYPES = {
        # Core UML structural elements
        "uml:Model",
        "uml:Package",
        "uml:Class",
        "uml:Interface",
        "uml:Component",
        "uml:Port",
        "uml:Property",
        "uml:Operation",
        "uml:Parameter",
        "uml:DataType",
        "uml:Enumeration",
        "uml:EnumerationLiteral",
        "uml:PrimitiveType",
        "uml:Stereotype",
        # UML Behavioral elements
        "uml:Actor",
        "uml:UseCase",
        "uml:StateMachine",
        "uml:State",
        "uml:Activity",
        "uml:Action",
        "uml:Transition",
        "uml:Interaction",
        "uml:Lifeline",
        "uml:Message",
        # UML Instance specifications
        "uml:InstanceSpecification",
        "uml:Slot",
        # UML Constraints and comments (now as nodes for traceability)
        "uml:Constraint",
        "uml:Comment",
        # UML Associations as first-class elements
        "uml:Association",
        "uml:AssociationClass",
        # SysML specific
        "sysml:Block",
        "sysml:Requirement",
        "sysml:ValueType",
        "sysml:FlowPort",
        "sysml:InterfaceBlock",
        # AP239 - Product Life Cycle Support (Level 1: Systems Engineering Core)
        # Requirements Management
        "Requirement",
        "RequirementVersion",
        "RequirementSource",
        "RequirementAssignment",
        "RequirementSatisfactionAssertion",
        "RequirementRelationship",
        # Analysis & Simulation
        "Analysis",
        "AnalysisModel",
        "AnalysisVersion",
        "AnalysisRepresentationContext",
        "AnalysisModelObject",
        "AnalysisDisciplineDefinition",
        # Approvals & Workflow
        "Approval",
        "ApprovalAssignment",
        "ApprovalRelationship",
        "Certification",
        "CertificationAssignment",
        # Documents & Evidence
        "Document",
        "DocumentDefinition",
        "DocumentVersion",
        "DocumentVersionRelationship",
        "DocumentRelationship",
        "Evidence",
        "DigitalDocumentDefinition",
        "DigitalFile",
        # Lifecycle & Configuration
        "Activity",
        "ActivityMethod",
        "ActivityAssignment",
        "ActivityRelationship",
        "Effectivity",
        "DatedEffectivity",
        "EffectivityAssignment",
        "BreakdownElement",
        "BreakdownVersion",
        "BreakdownElementVersion",
        "Breakdown",
        "BreakdownRelationship",
        # Events & Conditions
        "Event",
        "EventAssignment",
        "Condition",
        "ConditionEvaluation",
        "ConditionParameter",
        "ConditionAssignment",
        # Additional AP239 types
        "Assumption",
        "AssumptionAssignment",
        "Justification",
        "AdvisoryNote",
        "Collection",
        "CollectionVersion",
        "CollectionMembership",
        "Contract",
        "ContractAssignment",
        # AP242 - Managed Model-Based 3D Engineering (Level 2: CAD/Manufacturing)
        # Product Structure
        "Part",
        "PartVersion",
        "PartView",
        "Assembly",
        "AssemblyDefinition",
        "AssemblyViewRelationship",
        "AssemblyOccurrenceRelationship",
        "IndividualPart",
        "IndividualPartVersion",
        "IndividualPartView",
        # Geometry & CAD
        "GeometricModel",
        "ShapeRepresentation",
        "GeometricRepresentation",
        "GeometricRepresentationContext",
        "GeometricCoordinateSpace",
        "ComponentPlacement",
        "ExternalGeometricModel",
        "ComposedGeometricModel",
        # Materials & Properties
        "Material",
        "MaterialProperty",
        "PropertyValueRepresentation",
        "MeasureQualification",
        # Manufacturing
        "MakeFrom",
        "PhysicalBreakdownElementViewAssociation",
        "FunctionalBreakdownElementViewAssociation",
        # AP242 Additional types
        "AlternativeSolution",
        "ConfiguredAssemblyEffectivity",
        "DeltaChange",
        "Envelope",
        "EvaluatedCharacteristic",
        "EvaluatedRequirement",
        # AP243 - Reference Data & Ontologies (Level 3: Foundation)
        # Reference Ontologies
        "ExternalOwlClass",
        "ExternalOwlObject",
        "ExternalClassSystem",
        "ExternalLibrary",
        # Units & Measures
        "ExternalUnit",
        "ExternalTypeQualifier",
        "ExternalValue",
        # Value Types & Classifications
        "ExternalPropertyDefinition",
        "ExternalRefBaseObject",
        "Class",  # AP239/AP243 classification class
        "ClassAttribute",
        "Classification",
        "ClassificationRelationship",
        # Additional AP243 types
        "ExternalItem",
        "ApplicationDomain",
        "DataEnvironment",
        "ExchangeContext",
        "FormatProperty",
        "File",
        "Hardcopy",
    }

    # Elements that should be created as RELATIONSHIPS (connect nodes)
    RELATIONSHIP_TYPES = {
        # UML/SysML relationships
        "uml:Generalization",  # Inheritance
        "uml:Realization",  # Interface realization
        "uml:Dependency",  # General dependency
        "uml:Usage",  # Usage dependency
        "uml:Abstraction",  # Abstraction relationship
        "uml:Connector",  # Instance-level connection
        "uml:InformationFlow",  # Information flow
        "sysml:Allocate",  # SysML allocation
        "sysml:Satisfy",  # Requirement satisfaction
        "sysml:Verify",  # Requirement verification
        "sysml:Refine",  # Requirement refinement
        "sysml:Trace",  # Traceability link
        # AP239 relationships (Product Life Cycle Support)
        "SATISFIES",  # Requirement → Design element
        "VERIFIES",  # Test/Analysis → Requirement
        "REFINES",  # Requirement → Sub-requirement
        "APPROVES",  # Approval → Artifact
        "ANALYZES",  # Analysis → Model/Part
        "REQUIRES",  # Requirement → Requirement
        "DOCUMENTS",  # Document → Artifact
        "TRACES_TO",  # Traceability link
        "DECOMPOSES_INTO",  # Breakdown hierarchy
        "APPLIES_TO",  # Effectivity → Configuration
        "ASSIGNED_TO",  # Assignment relationships
        "CERTIFIES",  # Certification → Artifact
        "RELATES_TO",  # Generic relationship
        # AP242 relationships (CAD/Manufacturing)
        "HAS_GEOMETRY",  # Part → GeometricModel
        "USES_MATERIAL",  # Part → Material
        "ASSEMBLES_WITH",  # Part → Part (assembly)
        "PLACED_IN",  # Component → Assembly
        "HAS_REPRESENTATION",  # Part → ShapeRepresentation
        "MAKES_FROM",  # Manufacturing → Part
        "HAS_VERSION",  # Part → PartVersion
        "HAS_VIEW",  # Part → PartView
        "ALTERNATIVE_TO",  # AlternativeSolution
        # AP243 relationships (Reference Data & Ontologies)
        "CLASSIFIED_AS",  # Any node → ExternalOwlClass
        "HAS_UNIT",  # Property → ExternalUnit
        "HAS_VALUE_TYPE",  # Property → ValueType
        "REFERENCES",  # External reference
        # Cross-Level Hierarchical Relationships (AP239 → AP242 → AP243)
        "SATISFIED_BY_PART",  # AP239 Requirement → AP242 Part
        "ANALYZED_BY_MODEL",  # AP239 Analysis → AP242 GeometricModel
        "APPROVED_FOR_VERSION",  # AP239 Approval → AP242 PartVersion
        "DOCUMENTED_BY",  # AP239 Document → AP242 Part
        "MATERIAL_CLASSIFIED_AS",  # AP242 Material → AP243 ExternalOwlClass
        "USES_UNIT",  # AP242 Property → AP243 ExternalUnit
        "HAS_REFERENCE_TYPE",  # AP242 → AP243 ValueType
        "REQUIREMENT_VALUE_TYPE",  # AP239 Requirement → AP243 ValueType
        "ANALYSIS_USES_UNIT",  # AP239 Analysis → AP243 ExternalUnit
    }

    # Elements that are METADATA (stored as properties, not separate nodes)
    METADATA_TYPES = {
        "uml:LiteralInteger",
        "uml:LiteralUnlimitedNatural",
        "uml:LiteralString",
        "uml:LiteralBoolean",
        "uml:LiteralReal",
        "uml:InstanceValue",
        "uml:ConnectorEnd",
        "uml:OpaqueExpression",
        "uml:Expression",
        "uml:Duration",
        "uml:TimeExpression",
    }

    # Containment relationships mapping (parent tag -> relationship type)
    CONTAINMENT_RELATIONSHIPS = {
        "packagedElement": "CONTAINS",
        "ownedAttribute": "HAS_ATTRIBUTE",
        "ownedOperation": "HAS_OPERATION",
        "ownedParameter": "HAS_PARAMETER",
        "ownedPort": "HAS_PORT",
        "ownedLiteral": "HAS_LITERAL",
        "nestedClassifier": "HAS_NESTED_CLASSIFIER",
        "ownedRule": "HAS_RULE",
        "ownedComment": "OWNS_COMMENT",
        "ownedBehavior": "HAS_BEHAVIOR",
        "ownedEnd": "HAS_END",
        "memberEnd": "HAS_MEMBER_END",
        "navigableOwnedEnd": "HAS_NAVIGABLE_END",
    }

    # Properties to extract from elements (complete metamodel attributes)
    ELEMENT_PROPERTIES = {
        "visibility",  # public, private, protected, package
        "isAbstract",  # boolean
        "isStatic",  # boolean
        "isReadOnly",  # boolean
        "isDerived",  # boolean
        "isDerivedUnion",  # boolean
        "isLeaf",  # boolean
        "isOrdered",  # boolean
        "isUnique",  # boolean
        "aggregation",  # none, shared, composite
        "direction",  # in, out, inout, return
        "lower",  # multiplicity lower bound
        "upper",  # multiplicity upper bound
        "default",  # default value
        "body",  # constraint/comment body
        "language",  # expression language
        "value",  # literal values
    }

    # AP-level classification based on element type (ISO 10303 hierarchy)
    AP_LEVEL_MAP = {
        # AP239 – Product Life Cycle Support (Level 1: SE Core)
        "Requirement": "AP239", "RequirementVersion": "AP239", "RequirementSource": "AP239",
        "RequirementAssignment": "AP239", "RequirementSatisfactionAssertion": "AP239",
        "RequirementRelationship": "AP239",
        "Analysis": "AP239", "AnalysisModel": "AP239", "AnalysisVersion": "AP239",
        "AnalysisRepresentationContext": "AP239", "AnalysisModelObject": "AP239",
        "AnalysisDisciplineDefinition": "AP239",
        "Approval": "AP239", "ApprovalAssignment": "AP239", "ApprovalRelationship": "AP239",
        "Certification": "AP239", "CertificationAssignment": "AP239",
        "Document": "AP239", "DocumentDefinition": "AP239", "DocumentVersion": "AP239",
        "DocumentVersionRelationship": "AP239", "DocumentRelationship": "AP239",
        "Evidence": "AP239", "DigitalDocumentDefinition": "AP239", "DigitalFile": "AP239",
        "Activity": "AP239", "ActivityMethod": "AP239", "ActivityAssignment": "AP239",
        "ActivityRelationship": "AP239",
        "Effectivity": "AP239", "DatedEffectivity": "AP239", "EffectivityAssignment": "AP239",
        "BreakdownElement": "AP239", "BreakdownVersion": "AP239",
        "BreakdownElementVersion": "AP239", "Breakdown": "AP239",
        "BreakdownRelationship": "AP239",
        "Event": "AP239", "EventAssignment": "AP239",
        "Condition": "AP239", "ConditionEvaluation": "AP239",
        "ConditionParameter": "AP239", "ConditionAssignment": "AP239",
        "Assumption": "AP239", "AssumptionAssignment": "AP239",
        "Justification": "AP239", "AdvisoryNote": "AP239",
        "Collection": "AP239", "CollectionVersion": "AP239",
        "CollectionMembership": "AP239",
        "Contract": "AP239", "ContractAssignment": "AP239",
        # AP242 – Managed Model-Based 3D Engineering (Level 2: CAD/Manufacturing)
        "Part": "AP242", "PartVersion": "AP242", "PartView": "AP242",
        "Assembly": "AP242", "AssemblyDefinition": "AP242",
        "AssemblyViewRelationship": "AP242", "AssemblyOccurrenceRelationship": "AP242",
        "IndividualPart": "AP242", "IndividualPartVersion": "AP242",
        "IndividualPartView": "AP242",
        "GeometricModel": "AP242", "ShapeRepresentation": "AP242",
        "GeometricRepresentation": "AP242", "GeometricRepresentationContext": "AP242",
        "GeometricCoordinateSpace": "AP242", "ComponentPlacement": "AP242",
        "ExternalGeometricModel": "AP242", "ComposedGeometricModel": "AP242",
        "Material": "AP242", "MaterialProperty": "AP242",
        "PropertyValueRepresentation": "AP242", "MeasureQualification": "AP242",
        "MakeFrom": "AP242",
        "PhysicalBreakdownElementViewAssociation": "AP242",
        "FunctionalBreakdownElementViewAssociation": "AP242",
        "AlternativeSolution": "AP242", "ConfiguredAssemblyEffectivity": "AP242",
        "DeltaChange": "AP242", "Envelope": "AP242",
        "EvaluatedCharacteristic": "AP242", "EvaluatedRequirement": "AP242",
        # AP243 – Reference Data & Ontologies (Level 3: Foundation)
        "ExternalOwlClass": "AP243", "ExternalOwlObject": "AP243",
        "ExternalClassSystem": "AP243", "ExternalLibrary": "AP243",
        "ExternalUnit": "AP243", "ExternalTypeQualifier": "AP243",
        "ExternalValue": "AP243",
        "ExternalPropertyDefinition": "AP243", "ExternalRefBaseObject": "AP243",
        "ClassAttribute": "AP243", "Classification": "AP243",
        "ClassificationRelationship": "AP243",
        "ExternalItem": "AP243", "ApplicationDomain": "AP243",
        "DataEnvironment": "AP243", "ExchangeContext": "AP243",
        "FormatProperty": "AP243", "File": "AP243", "Hardcopy": "AP243",
    }

    def __init__(self, connection: Neo4jConnection, enable_versioning: bool = True):
        """Initialize semantic loader with complete UML/SysML support"""
        self.conn = connection
        self.enable_versioning = enable_versioning
        self.load_timestamp = None
        self.namespaces = {
            "xmi": "http://www.omg.org/spec/XMI/20131001",
            "uml": "http://www.omg.org/spec/UML/20131001",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }
        self.element_cache: Dict[str, Dict] = {}  # Cache element data by ID

    def load_xmi_file(self, xmi_file_path: Path) -> dict:
        """
        Load XMI file into Neo4j following UML/SysML semantics

        Args:
            xmi_file_path: Path to XMI file

        Returns:
            Statistics about loaded data
        """
        from datetime import datetime

        # Set load timestamp for versioning
        if self.enable_versioning:
            self.load_timestamp = datetime.utcnow().isoformat()

        logger.info(f"🔍 Parsing XMI file: {xmi_file_path}")
        self._current_source_file = Path(xmi_file_path).name

        # Parse XML
        tree = etree.parse(str(xmi_file_path))
        root = tree.getroot()

        # Clear cache
        self.element_cache = {}

        stats = {}

        # Step 1: Extract all elements and classify them
        logger.info("📊 Analyzing XMI structure...")
        self._analyze_elements(root)

        # Step 2: Create nodes (first-class model elements)
        logger.info("✅ Creating model element nodes...")
        nodes_created = self._create_model_element_nodes(root)
        stats["nodes_created"] = nodes_created
        logger.info(f"Created {nodes_created} nodes")

        # Step 3: Create containment relationships (hierarchical structure)
        logger.info("🌳 Creating containment hierarchy...")
        containment_rels = self._create_containment_relationships(root)
        stats["containment_relationships"] = containment_rels
        logger.info(f"Created {containment_rels} containment relationships")

        # Step 4: Create semantic relationships (associations, generalizations, etc.)
        logger.info("🔗 Creating semantic relationships...")
        semantic_rels = self._create_semantic_relationships(root)
        stats["semantic_relationships"] = semantic_rels
        logger.info(f"Created {semantic_rels} semantic relationships")

        # Step 5: Add type references
        logger.info("🏷️  Creating type references...")
        type_rels = self._create_type_relationships(root)
        stats["type_relationships"] = type_rels
        logger.info(f"Created {type_rels} type relationships")

        # Step 6: Attach metadata (comments, literals) as properties
        logger.info("📝 Attaching metadata as properties...")
        metadata_attached = self._attach_metadata(root)
        stats["metadata_attached"] = metadata_attached
        logger.info(f"Attached {metadata_attached} metadata properties")

        logger.info(f"✨ XMI loading complete! Stats: {stats}")
        return stats

    def _analyze_elements(self, root: etree.Element) -> None:
        """Analyze and classify all elements in the XMI"""
        all_elements = root.xpath("//*[@xmi:type]", namespaces=self.namespaces)

        node_count = 0
        rel_count = 0
        meta_count = 0

        for elem in all_elements:
            elem_type = elem.get("{http://www.omg.org/spec/XMI/20131001}type")
            if elem_type in self.NODE_TYPES:
                node_count += 1
            elif elem_type in self.RELATIONSHIP_TYPES:
                rel_count += 1
            elif elem_type in self.METADATA_TYPES:
                meta_count += 1

        logger.info(
            f"  Nodes: {node_count}, Relationships: {rel_count}, Metadata: {meta_count}"
        )

    def _get_element_name(self, elem: etree.Element) -> str:
        """Extract name from element (attribute or child element)"""
        # Try name attribute first
        name = elem.get("name", "")
        if name:
            return name

        # Try child name element
        name_elem = elem.find("name")
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()

        return ""

    def _create_model_element_nodes(self, root: etree.Element) -> int:
        """Create nodes for first-class model elements with full property extraction"""
        count = 0
        batch_size = 500
        batch = []

        # Find all elements that should be nodes
        for node_type in self.NODE_TYPES:
            elements = root.xpath(
                f"//*[@xmi:type='{node_type}']", namespaces=self.namespaces
            )

            for elem in elements:
                elem_id = elem.get("{http://www.omg.org/spec/XMI/20131001}id")
                if not elem_id:
                    continue

                name = self._get_element_name(elem)
                elem_type = elem.get("{http://www.omg.org/spec/XMI/20131001}type")

                # Get simple label from type (e.g., uml:Class -> Class)
                label = elem_type.split(":")[-1] if ":" in elem_type else elem_type

                # Create detailed labels list
                labels = [label]

                # Check for Domain Entities (AP239, AP242, AP243) to align with UI/UX
                # These are usually defined as Classes in the XMI but need specific labels for the Application
                domain_entities = {
                    # AP243 (MoSSEC)
                    "ModelInstance", "Study", "ActualActivity", "AssociativeModelNetwork",
                    "ModelType", "Method", "Evaluation", "Result",
                    
                    # AP242 (CAD)
                    "Part", "PartVersion", "Assembly", "GeometricModel",
                    "ShapeRepresentation", "Material", "ComponentBasedSolid",
                    
                    # AP239 (PLCS)
                    "Requirement", "RequirementVersion", "breakdown", "WorkOrder",
                    "Activity", "Observation", "ProductConfiguration",
                    "Document", "Person", "Organization"
                }

                if name in domain_entities:
                    labels.append(name)

                # Extract xmi:uuid (stable OMG identifier)
                xmi_uuid = elem.get("{http://www.omg.org/spec/XMI/20131001}uuid")

                # Extract ALL UML/SysML properties
                properties = self._extract_element_properties(elem, elem_type)
                properties.update(
                    {
                        "id": elem_id,
                        "name": name,
                        "type": elem_type,
                        "source": "XMI",
                        "source_file": self._current_source_file,
                    }
                )

                # Store xmi:uuid when present (stable cross-tool identifier)
                if xmi_uuid:
                    properties["uuid"] = xmi_uuid
                    properties["xmi_uuid"] = xmi_uuid

                # Store xmi:id for traceability
                properties["xmi_id"] = elem_id

                # Classify AP level based on element label
                ap_level = self.AP_LEVEL_MAP.get(label)
                if ap_level:
                    properties["ap_level"] = ap_level
                else:
                    # Default: MoSSEC XMI maps to AP243
                    properties["ap_level"] = "AP243"

                # Add version metadata if enabled
                if self.enable_versioning and self.load_timestamp:
                    properties["version"] = 1
                    properties["createdAt"] = self.load_timestamp
                    properties["modifiedAt"] = self.load_timestamp
                    properties["loadSource"] = "XMI"

                # Add MBSEElement as base label for all nodes
                if "MBSEElement" not in labels:
                    labels.append("MBSEElement")

                # Cache element data
                self.element_cache[elem_id] = {
                    "id": elem_id,
                    "name": name,
                    "type": elem_type,
                    "labels": labels,
                    "label": label,
                    "element": elem,
                    "properties": properties,
                }

                batch.append({"id": elem_id, "labels": labels, "properties": properties})

                if len(batch) >= batch_size:
                    self._create_node_batch(batch)
                    count += len(batch)
                    batch = []

        # Create remaining nodes
        if batch:
            self._create_node_batch(batch)
            count += len(batch)

        return count

    def _extract_element_properties(self, elem: etree.Element, elem_type: str) -> Dict:
        """Extract all standardized UML/SysML properties from element"""
        properties = {}

        # Extract boolean properties (try attribute first, then child element)
        for bool_prop in [
            "isAbstract",
            "isStatic",
            "isReadOnly",
            "isDerived",
            "isDerivedUnion",
            "isLeaf",
            "isOrdered",
            "isUnique",
        ]:
            value = elem.get(bool_prop)
            if not value:
                child = elem.find(bool_prop)
                if child is not None and child.text:
                    value = child.text.strip()
            if value:
                properties[bool_prop] = value.lower() == "true"

        # Extract enumeration properties (try attribute first, then child element)
        for enum_prop in ["visibility", "aggregation", "direction"]:
            value = elem.get(enum_prop)
            if not value:
                child = elem.find(enum_prop)
                if child is not None and child.text:
                    value = child.text.strip()
            if value:
                properties[enum_prop] = value

        # Extract multiplicity from lowerValue/upperValue child elements
        lower_value = elem.find("lowerValue")
        if lower_value is not None:
            lower = lower_value.get("value")
            if lower:
                properties["lower"] = int(lower) if lower.isdigit() else lower
            else:
                # Default for LiteralInteger without value is 0
                properties["lower"] = 0

        upper_value = elem.find("upperValue")
        if upper_value is not None:
            upper = upper_value.get("value")
            if upper:
                # Handle '*' for unlimited
                properties["upper"] = (
                    -1 if upper == "*" else (int(upper) if upper.isdigit() else upper)
                )
            else:
                # Default for LiteralUnlimitedNatural without value is unlimited (*)
                if "LiteralUnlimitedNatural" in upper_value.get(
                    "{http://www.omg.org/spec/XMI/20131001}type", ""
                ):
                    properties["upper"] = -1

        # Extract default value
        default = elem.get("default")
        if default:
            properties["default"] = default

        # Extract body (for Constraints, Comments, OpaqueExpressions)
        body_elem = elem.find("body")
        if body_elem is not None and body_elem.text:
            # Replace " | " with newlines for better formatting
            body_text = body_elem.text.strip().replace(" | ", "\n")
            properties["body"] = body_text

        # Extract language (for OpaqueExpressions)
        language_elem = elem.find("language")
        if language_elem is not None and language_elem.text:
            properties["language"] = language_elem.text.strip()

        # Extract value (for Literals) - attribute
        value = elem.get("value")
        if value:
            properties["value"] = value

        # Extract href (external references)
        href = elem.get("href")
        if href:
            properties["href"] = href

        # Extract type reference (for Properties, Slots, etc.)
        type_elem = elem.find("type")
        if type_elem is not None:
            type_ref = type_elem.get("{http://www.omg.org/spec/XMI/20131001}idref")
            if type_ref:
                properties["type_ref"] = type_ref

        # Also check type attribute
        type_attr = elem.get("type")
        if type_attr and "type_ref" not in properties:
            properties["type_ref"] = type_attr

        return properties

    def _create_node_batch(self, batch: List[Dict]) -> None:
        """Create a batch of nodes using MERGE on id for idempotent re-runs.
        Falls back to apoc.create.node for dynamic labels with MERGE semantics."""
        query = """
        UNWIND $nodes AS node
        CALL apoc.merge.node(node.labels, {id: node.properties.id}, node.properties) YIELD node AS n
        RETURN count(n) AS created
        """
        self.conn.execute_query(query, {"nodes": batch})

    def _create_containment_relationships(self, root: etree.Element) -> int:
        """Create hierarchical containment relationships"""
        count = 0
        batch_size = 500
        batch = []

        # Iterate through all cached elements
        for elem_id, elem_data in self.element_cache.items():
            elem = elem_data["element"]

            # Check all children
            for child in elem:
                child_id = child.get("{http://www.omg.org/spec/XMI/20131001}id")
                child_type = child.get("{http://www.omg.org/spec/XMI/20131001}type")

                # Skip if child is not a first-class element
                if not child_id or child_type not in self.NODE_TYPES:
                    continue

                # Determine relationship type based on child's tag
                rel_type = self.CONTAINMENT_RELATIONSHIPS.get(child.tag, "CONTAINS")

                batch.append(
                    {"parent_id": elem_id, "child_id": child_id, "rel_type": rel_type}
                )

                if len(batch) >= batch_size:
                    self._create_containment_batch(batch)
                    count += len(batch)
                    batch = []

        # Create remaining relationships
        if batch:
            self._create_containment_batch(batch)
            count += len(batch)

        return count

    def _create_containment_batch(self, batch: List[Dict]) -> None:
        """Create a batch of containment relationships using MERGE for idempotency"""
        query = """
        UNWIND $rels AS rel
        MATCH (parent:MBSEElement {id: rel.parent_id})
        MATCH (child:MBSEElement {id: rel.child_id})
        CALL apoc.merge.relationship(parent, rel.rel_type, {}, {}, child) YIELD rel AS r
        RETURN count(r) AS created
        """
        self.conn.execute_query(query, {"rels": batch})

    def _create_semantic_relationships(self, root: etree.Element) -> int:
        """Create semantic relationships (associations, generalizations, connectors)"""
        count = 0

        # Handle Associations
        count += self._create_associations(root)

        # Handle Generalizations
        count += self._create_generalizations(root)

        # Handle Connectors
        count += self._create_connectors(root)

        # Handle Dependencies, Realizations, etc.
        count += self._create_other_relationships(root)

        return count

    def _create_associations(self, root: etree.Element) -> int:
        """Create Association relationships from Association nodes using memberEnd references"""
        # Note: Association NODES are already created in _create_model_element_nodes
        # Here we create the ASSOCIATES_WITH relationships based on memberEnds
        # AND update Association nodes with memberEnd names for better display

        count = 0
        batch = []
        assoc_updates = []

        # Find all Association nodes in cache
        for elem_id, elem_data in self.element_cache.items():
            if elem_data["type"] != "uml:Association":
                continue

            elem = elem_data["element"]

            # Find memberEnd references (can be child elements or attributes)
            member_end_refs = []

            # Try as child elements first
            member_ends = elem.findall("memberEnd")
            for me in member_ends:
                ref = me.get("{http://www.omg.org/spec/XMI/20131001}idref")
                if ref:
                    member_end_refs.append(ref)

            # If not found, try memberEnd attribute (space-separated list)
            if not member_end_refs:
                member_end_attr = elem.get("memberEnd")
                if member_end_attr:
                    member_end_refs = member_end_attr.split()

            # Collect memberEnd names for display
            member_end_names = []
            member_end_types = []
            for ref in member_end_refs:
                if ref in self.element_cache:
                    end_data = self.element_cache[ref]
                    end_name = end_data.get("name", "")
                    # If property has no name, try to get its type
                    if not end_name and "properties" in end_data:
                        type_ref = end_data["properties"].get("type_ref")
                        if type_ref and type_ref in self.element_cache:
                            end_name = f"[{self.element_cache[type_ref].get('name', 'unnamed')}]"
                        else:
                            end_name = "[unnamed]"
                    member_end_names.append(end_name or "[unnamed]")

                    # Get the type this property is typed by
                    if "properties" in end_data:
                        type_ref = end_data["properties"].get("type_ref")
                        if type_ref and type_ref in self.element_cache:
                            member_end_types.append(
                                self.element_cache[type_ref].get("name", "")
                            )

            # Update Association node with memberEnd information
            if member_end_names:
                display_name = " ↔ ".join(member_end_names)
                assoc_updates.append(
                    {
                        "id": elem_id,
                        "member_ends": ", ".join(member_end_names),
                        "end_types": ", ".join(filter(None, member_end_types)),
                        "display_name": display_name,
                    }
                )

            # Create relationships between memberEnds
            if len(member_end_refs) >= 2:
                end1_ref = member_end_refs[0]
                end2_ref = member_end_refs[1]

                if end1_ref in self.element_cache and end2_ref in self.element_cache:
                    batch.append(
                        {
                            "source_id": end1_ref,
                            "target_id": end2_ref,
                            "assoc_id": elem_id,
                            "assoc_name": elem_data["name"] or "Association",
                        }
                    )

        # Update Association nodes with memberEnd information
        if assoc_updates:
            update_query = """
            UNWIND $updates AS upd
            MATCH (a:Association {id: upd.id})
            SET a.member_ends = upd.member_ends,
                a.end_types = upd.end_types,
                a.display_name = upd.display_name
            RETURN count(a) AS updated
            """
            result = self.conn.execute_query(update_query, {"updates": assoc_updates})
            logger.info(
                f"Updated {len(assoc_updates)} Association nodes with memberEnd information"
            )

        if batch:
            query = """
            UNWIND $rels AS rel
            MATCH (source:MBSEElement {id: rel.source_id})
            MATCH (target:MBSEElement {id: rel.target_id})
            MATCH (assoc:Association {id: rel.assoc_id})
            CALL apoc.merge.relationship(source, 'ASSOCIATES_WITH', {
                association_id: rel.assoc_id,
                association_name: rel.assoc_name
            }, {}, target) YIELD rel AS r
            RETURN count(r) AS created
            """
            self.conn.execute_query(query, {"rels": batch})
            count = len(batch)

        return count

    def _create_generalizations(self, root: etree.Element) -> int:
        """Create Generalization relationships (inheritance)"""
        generalizations = root.xpath(
            "//*[@xmi:type='uml:Generalization']", namespaces=self.namespaces
        )
        count = 0
        batch = []

        for gen in generalizations:
            gen_id = gen.get("{http://www.omg.org/spec/XMI/20131001}id")

            # Find general (parent) reference
            general_elem = gen.find("general")
            if general_elem is not None:
                general_ref = general_elem.get(
                    "{http://www.omg.org/spec/XMI/20131001}idref"
                )

                # Find specific (child) - it's the parent element of the generalization
                specific_elem = gen.getparent()
                if specific_elem is not None:
                    specific_id = specific_elem.get(
                        "{http://www.omg.org/spec/XMI/20131001}id"
                    )

                    if (
                        general_ref
                        and specific_id
                        and general_ref in self.element_cache
                        and specific_id in self.element_cache
                    ):
                        batch.append(
                            {
                                "child_id": specific_id,
                                "parent_id": general_ref,
                                "gen_id": gen_id,
                            }
                        )

        if batch:
            query = """
            UNWIND $rels AS rel
            MATCH (child:MBSEElement {id: rel.child_id})
            MATCH (parent:MBSEElement {id: rel.parent_id})
            CALL apoc.merge.relationship(child, 'GENERALIZES', {generalization_id: rel.gen_id}, {}, parent) YIELD rel AS r
            RETURN count(r) AS created
            """
            self.conn.execute_query(query, {"rels": batch})
            count = len(batch)

        return count

    def _create_connectors(self, root: etree.Element) -> int:
        """Create Connector relationships between ports/properties"""
        # Find Connectors from cache (they're in RELATIONSHIP_TYPES, not created as nodes)
        connectors = root.xpath(
            "//*[@xmi:type='uml:Connector']", namespaces=self.namespaces
        )
        count = 0
        batch = []

        for connector in connectors:
            connector_id = connector.get("{http://www.omg.org/spec/XMI/20131001}id")

            # Find end children (ConnectorEnd elements)
            ends = connector.findall("end")

            if len(ends) >= 2:
                # Get role references from nested role elements
                role_refs = []
                for end in ends:
                    # Look for role child element with idref
                    role_elem = end.find("role")
                    if role_elem is not None:
                        role_ref = role_elem.get(
                            "{http://www.omg.org/spec/XMI/20131001}idref"
                        )
                        if role_ref:
                            role_refs.append(role_ref)
                        else:
                            # Check for href (external reference) - skip these
                            href = role_elem.get("href")
                            if href:
                                role_refs.append(None)  # Mark as external

                # Only create relationship if both roles are internal (in cache)
                if len(role_refs) >= 2 and role_refs[0] and role_refs[1]:
                    if (
                        role_refs[0] in self.element_cache
                        and role_refs[1] in self.element_cache
                    ):
                        batch.append(
                            {
                                "source_id": role_refs[0],
                                "target_id": role_refs[1],
                                "connector_id": connector_id,
                            }
                        )

        if batch:
            query = """
            UNWIND $rels AS rel
            MATCH (source:MBSEElement {id: rel.source_id})
            MATCH (target:MBSEElement {id: rel.target_id})
            CALL apoc.merge.relationship(source, 'CONNECTED_BY', {connector_id: rel.connector_id}, {}, target) YIELD rel AS r
            RETURN count(r) AS created
            """
            self.conn.execute_query(query, {"rels": batch})
            count = len(batch)

        return count

    def _create_other_relationships(self, root: etree.Element) -> int:
        """Create other relationship types (Dependency, Realization, Usage)"""
        count = 0

        rel_mappings = {
            "uml:Dependency": ("DEPENDS_ON", "supplier", "client"),
            "uml:Realization": ("REALIZES", "supplier", "client"),
            "uml:Usage": ("USES", "supplier", "client"),
        }

        for rel_type, (neo4j_rel, target_attr, source_attr) in rel_mappings.items():
            elements = root.xpath(
                f"//*[@xmi:type='{rel_type}']", namespaces=self.namespaces
            )
            batch = []

            for elem in elements:
                elem_id = elem.get("{http://www.omg.org/spec/XMI/20131001}id")

                # Try to find references as child elements or attributes
                target_elem = elem.find(target_attr)
                target_ref = (
                    target_elem.get("{http://www.omg.org/spec/XMI/20131001}idref")
                    if target_elem is not None
                    else elem.get(target_attr)
                )

                source_elem = elem.find(source_attr)
                source_ref = (
                    source_elem.get("{http://www.omg.org/spec/XMI/20131001}idref")
                    if source_elem is not None
                    else elem.get(source_attr)
                )

                if (
                    source_ref
                    and target_ref
                    and source_ref in self.element_cache
                    and target_ref in self.element_cache
                ):
                    batch.append(
                        {
                            "source_id": source_ref,
                            "target_id": target_ref,
                            "rel_id": elem_id,
                            "rel_type": neo4j_rel,
                        }
                    )

            if batch:
                query = """
                UNWIND $rels AS rel
                MATCH (source:MBSEElement {id: rel.source_id})
                MATCH (target:MBSEElement {id: rel.target_id})
                CALL apoc.merge.relationship(source, rel.rel_type, {relationship_id: rel.rel_id}, {}, target) YIELD rel AS r
                RETURN count(r) AS created
                """
                self.conn.execute_query(query, {"rels": batch})
                count += len(batch)

        return count

    def _create_type_relationships(self, root: etree.Element) -> int:
        """Create TYPED_BY relationships for properties with type references"""
        count = 0
        batch = []

        # Properties and Parameters often have type references
        for elem_id, elem_data in self.element_cache.items():
            elem = elem_data["element"]
            elem_type = elem_data["type"]

            # Check if element has a type reference
            if elem_type in ["uml:Property", "uml:Parameter", "uml:Port"]:
                # First try attribute
                type_ref = elem.get("type")

                # If not found, try child element with idref
                if not type_ref:
                    type_elem = elem.find("type")
                    if type_elem is not None:
                        type_ref = type_elem.get(
                            "{http://www.omg.org/spec/XMI/20131001}idref"
                        )

                if type_ref and type_ref in self.element_cache:
                    batch.append({"element_id": elem_id, "type_id": type_ref})

        if batch:
            query = """
            UNWIND $rels AS rel
            MATCH (element:MBSEElement {id: rel.element_id})
            MATCH (type:MBSEElement {id: rel.type_id})
            CALL apoc.merge.relationship(element, 'TYPED_BY', {}, {}, type) YIELD rel AS r
            RETURN count(r) AS created
            """
            self.conn.execute_query(query, {"rels": batch})
            count = len(batch)

        return count

    def _attach_metadata(self, root: etree.Element) -> int:
        """Attach inline metadata and create relationships to Comment nodes"""
        count = 0

        # For elements with inline comments (not separate Comment nodes), attach as property
        for elem_id, elem_data in self.element_cache.items():
            elem = elem_data["element"]
            updates = {}

            # Check if element has inline comment attribute
            inline_comment = elem.get("comment")
            if inline_comment:
                updates["comment"] = inline_comment.replace(" | ", "\n")

            # Find literal values for properties
            if elem_data["type"] == "uml:Property":
                # Check for default values from literal elements
                for literal_type in [
                    "LiteralInteger",
                    "LiteralString",
                    "LiteralUnlimitedNatural",
                    "LiteralBoolean",
                    "LiteralReal",
                ]:
                    literals = elem.xpath(
                        f".//defaultValue[@xmi:type='uml:{literal_type}']",
                        namespaces=self.namespaces,
                    )
                    if literals:
                        literal = literals[0]
                        value = literal.get("value")
                        if value:
                            updates["defaultValue"] = value
                            break

            # Update node with metadata
            if updates:
                query = """
                MATCH (n:MBSEElement {id: $id})
                SET n += $properties
                RETURN n
                """
                self.conn.execute_query(query, {"id": elem_id, "properties": updates})
                count += 1

        # Create HAS_COMMENT relationships from elements to Comment nodes
        comment_rels = self._create_comment_relationships(root)
        count += comment_rels

        return count

    def _create_comment_relationships(self, root: etree.Element) -> int:
        """Create relationships from elements to their Comment nodes"""
        count = 0
        batch = []

        # Find all Comment nodes and connect them to their annotated elements
        for elem_id, elem_data in self.element_cache.items():
            if elem_data["type"] != "uml:Comment":
                continue

            elem = elem_data["element"]

            # Find annotatedElement references
            annotated_refs = []

            # Try as child elements
            annotated_elems = elem.findall("annotatedElement")
            for ae in annotated_elems:
                ref = ae.get("{http://www.omg.org/spec/XMI/20131001}idref")
                if ref:
                    annotated_refs.append(ref)

            # Try as attribute (space-separated)
            if not annotated_refs:
                annotated_attr = elem.get("annotatedElement")
                if annotated_attr:
                    annotated_refs = annotated_attr.split()

            # Create relationships
            # Use a set to prevent duplicate relationships between same comment and target
            processed_targets = set()
            for target_id in annotated_refs:
                if target_id in self.element_cache and target_id not in processed_targets:
                    batch.append({"comment_id": elem_id, "target_id": target_id})
                    processed_targets.add(target_id)

        if batch:
            query = """
            UNWIND $rels AS rel
            MATCH (comment:Comment {id: rel.comment_id})
            MATCH (target:MBSEElement {id: rel.target_id})
            CALL apoc.merge.relationship(target, 'HAS_COMMENT', {}, {}, comment) YIELD rel AS r
            RETURN count(r) AS created
            """
            self.conn.execute_query(query, {"rels": batch})
            count = len(batch)

        return count

    def clear_graph(self) -> None:
        """Clear all nodes and relationships from the graph"""
        logger.info("Clearing graph...")
        query = "MATCH (n) DETACH DELETE n"
        self.conn.execute_query(query)
        logger.info("Graph cleared!")

    def create_constraints_and_indexes(self) -> None:
        """Create uniqueness constraints and indexes for graph integrity.
        Must be called BEFORE loading data for MERGE to be efficient."""
        logger.info("Creating uniqueness constraints and indexes...")

        constraints = [
            # MBSEElement: unique on xmi:id
            "CREATE CONSTRAINT mbse_element_id IF NOT EXISTS FOR (n:MBSEElement) REQUIRE n.id IS UNIQUE",
            # OSLC ontology nodes
            "CREATE CONSTRAINT ontology_uri IF NOT EXISTS FOR (n:Ontology) REQUIRE n.uri IS UNIQUE",
            "CREATE CONSTRAINT ontology_class_uri IF NOT EXISTS FOR (n:OntologyClass) REQUIRE n.uri IS UNIQUE",
            "CREATE CONSTRAINT ontology_property_uri IF NOT EXISTS FOR (n:OntologyProperty) REQUIRE n.uri IS UNIQUE",
            "CREATE CONSTRAINT ext_ontology_uri IF NOT EXISTS FOR (n:ExternalOntology) REQUIRE n.uri IS UNIQUE",
            "CREATE CONSTRAINT ext_owl_class_uri IF NOT EXISTS FOR (n:ExternalOwlClass) REQUIRE n.uri IS UNIQUE",
            # XSD nodes
            "CREATE CONSTRAINT xsd_element_id IF NOT EXISTS FOR (n:XSDElement) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT xsd_schema_id IF NOT EXISTS FOR (n:XSDSchema) REQUIRE n.id IS UNIQUE",
        ]

        indexes = [
            # Performance indexes for frequent lookups
            "CREATE INDEX mbse_element_name IF NOT EXISTS FOR (n:MBSEElement) ON (n.name)",
            "CREATE INDEX mbse_element_uuid IF NOT EXISTS FOR (n:MBSEElement) ON (n.uuid)",
            "CREATE INDEX mbse_element_ap_level IF NOT EXISTS FOR (n:MBSEElement) ON (n.ap_level)",
            "CREATE INDEX mbse_element_source IF NOT EXISTS FOR (n:MBSEElement) ON (n.source)",
        ]

        for stmt in constraints + indexes:
            try:
                self.conn.execute_query(stmt)
                logger.info(f"  ✓ {stmt.split('IF NOT EXISTS')[0].strip()}")
            except Exception as e:
                # Constraint may already exist — that's fine
                logger.debug(f"  Skipped (may already exist): {e}")

        logger.info("Constraints and indexes ready.")

    def create_cross_schema_links(self) -> int:
        """Create cross-schema relationships linking XMI ↔ XSD ↔ OSLC nodes.
        
        Strategies:
        1. XMI Class ↔ XSD ComplexType: Match by name (same domain entity)
        2. XMI Class ↔ OSLC OntologyClass: Match domain entities to OSLC vocabulary
        3. XMI Class ↔ ExternalOwlClass: Connect to OSLC owl classes by name
        """
        total = 0

        # --- Strategy 1: XMI Class ↔ XSD ComplexType by name ---
        logger.info("Linking XMI Classes ↔ XSD ComplexTypes by name...")
        result = self.conn.execute_query("""
            MATCH (xmi:Class:MBSEElement)
            MATCH (xsd:XSDComplexType)
            WHERE toLower(xmi.name) = toLower(xsd.name)
            MERGE (xmi)-[:SAME_AS {link_type: 'xmi_xsd_name_match', source: 'cross_schema_linker'}]->(xsd)
            RETURN count(*) AS linked
        """)
        n = result[0]["linked"] if result else 0
        total += n
        logger.info(f"  XMI↔XSD name matches: {n}")

        # --- Strategy 2: XMI domain entities ↔ OSLC OntologyClass by label ---
        logger.info("Linking XMI entities ↔ OSLC OntologyClass by label...")
        result = self.conn.execute_query("""
            MATCH (xmi:MBSEElement)
            WHERE xmi.name IS NOT NULL AND xmi.name <> ''
            MATCH (oslc:OntologyClass)
            WHERE toLower(xmi.name) = toLower(oslc.label)
            MERGE (xmi)-[:MAPS_TO_OSLC {link_type: 'name_to_oslc_class', source: 'cross_schema_linker'}]->(oslc)
            RETURN count(*) AS linked
        """)
        n = result[0]["linked"] if result else 0
        total += n
        logger.info(f"  XMI↔OSLC class matches: {n}")

        # --- Strategy 3: XMI domain entities ↔ ExternalOwlClass by name ---
        logger.info("Linking XMI entities ↔ ExternalOwlClass by name...")
        result = self.conn.execute_query("""
            MATCH (xmi:MBSEElement)
            WHERE xmi.name IS NOT NULL AND xmi.name <> ''
            MATCH (owl:ExternalOwlClass)
            WHERE toLower(xmi.name) = toLower(owl.name)
            MERGE (xmi)-[:MAPS_TO_ONTOLOGY {link_type: 'name_to_owl_class', source: 'cross_schema_linker'}]->(owl)
            RETURN count(*) AS linked
        """)
        n = result[0]["linked"] if result else 0
        total += n
        logger.info(f"  XMI↔ExternalOwlClass matches: {n}")

        # --- Strategy 4: Tag XSD nodes with source and ap_level ---
        logger.info("Tagging XSD nodes with source and ap_level...")
        result = self.conn.execute_query("""
            MATCH (n)
            WHERE any(lbl IN labels(n) WHERE lbl STARTS WITH 'XSD')
              AND n.source IS NULL
            SET n.source = 'XSD', n.ap_level = 'AP243'
            RETURN count(n) AS tagged
        """)
        n = result[0]["tagged"] if result else 0
        logger.info(f"  XSD nodes tagged: {n}")

        # --- Strategy 5: Fix ExternalOwlClass/ExternalOntology ap_level (int→string) ---
        logger.info("Normalizing ap_level on ExternalOwlClass/ExternalOntology...")
        self.conn.execute_query("""
            MATCH (n)
            WHERE (n:ExternalOwlClass OR n:ExternalOntology)
              AND n.ap_level IS NOT NULL
              AND NOT n.ap_level STARTS WITH 'AP'
            SET n.ap_level = 'AP' + toString(n.ap_level * 81),
                n.source = 'OSLC'
        """)
        # For integer 3 → AP243;  just set directly for safety
        self.conn.execute_query("""
            MATCH (n)
            WHERE (n:ExternalOwlClass OR n:ExternalOntology)
            SET n.ap_level = 'AP243', n.source = 'OSLC'
        """)
        logger.info("  ExternalOwlClass/ExternalOntology normalized to AP243.")

        logger.info(f"Cross-schema linking complete. Total links created: {total}")
        return total
