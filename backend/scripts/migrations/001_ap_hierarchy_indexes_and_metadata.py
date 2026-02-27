"""
Migration 001: AP hierarchy indexes and metadata
Converts the existing migrate_to_ap_hierarchy.cypher into the migration framework.
"""


def up(neo4j):
    """Create indexes and assign ap_level metadata to all node types."""
    # Phase 1 — AP239 indexes
    indexes = [
        "CREATE INDEX idx_requirement_name IF NOT EXISTS FOR (n:Requirement) ON (n.name)",
        "CREATE INDEX idx_requirement_id IF NOT EXISTS FOR (n:Requirement) ON (n.id)",
        "CREATE INDEX idx_requirement_version_name IF NOT EXISTS FOR (n:RequirementVersion) ON (n.name)",
        "CREATE INDEX idx_analysis_name IF NOT EXISTS FOR (n:Analysis) ON (n.name)",
        "CREATE INDEX idx_analysis_model_name IF NOT EXISTS FOR (n:AnalysisModel) ON (n.name)",
        "CREATE INDEX idx_approval_name IF NOT EXISTS FOR (n:Approval) ON (n.name)",
        "CREATE INDEX idx_document_name IF NOT EXISTS FOR (n:Document) ON (n.name)",
        "CREATE INDEX idx_activity_name IF NOT EXISTS FOR (n:Activity) ON (n.name)",
        "CREATE INDEX idx_breakdown_name IF NOT EXISTS FOR (n:Breakdown) ON (n.name)",
        "CREATE INDEX idx_event_name IF NOT EXISTS FOR (n:Event) ON (n.name)",
        # Phase 2 — AP242 indexes
        "CREATE INDEX idx_part_name IF NOT EXISTS FOR (n:Part) ON (n.name)",
        "CREATE INDEX idx_part_id IF NOT EXISTS FOR (n:Part) ON (n.id)",
        "CREATE INDEX idx_part_version_name IF NOT EXISTS FOR (n:PartVersion) ON (n.name)",
        "CREATE INDEX idx_assembly_name IF NOT EXISTS FOR (n:Assembly) ON (n.name)",
        "CREATE INDEX idx_geometric_model_name IF NOT EXISTS FOR (n:GeometricModel) ON (n.name)",
        "CREATE INDEX idx_shape_representation_name IF NOT EXISTS FOR (n:ShapeRepresentation) ON (n.name)",
        "CREATE INDEX idx_material_name IF NOT EXISTS FOR (n:Material) ON (n.name)",
        "CREATE INDEX idx_material_property_name IF NOT EXISTS FOR (n:MaterialProperty) ON (n.name)",
        "CREATE INDEX idx_component_placement_name IF NOT EXISTS FOR (n:ComponentPlacement) ON (n.name)",
        # Phase 3 — AP243 indexes
        "CREATE INDEX idx_external_owl_class_name IF NOT EXISTS FOR (n:ExternalOwlClass) ON (n.name)",
        "CREATE INDEX idx_external_unit_name IF NOT EXISTS FOR (n:ExternalUnit) ON (n.name)",
        "CREATE INDEX idx_external_property_def_name IF NOT EXISTS FOR (n:ExternalPropertyDefinition) ON (n.name)",
        "CREATE INDEX idx_classification_name IF NOT EXISTS FOR (n:Classification) ON (n.name)",
        "CREATE INDEX idx_value_type_name IF NOT EXISTS FOR (n:ValueType) ON (n.name)",
    ]

    for idx_stmt in indexes:
        neo4j.execute_query(idx_stmt)

    # Phase 4 — Assign ap_level metadata
    level_map = {
        "AP239": [
            "Requirement", "RequirementVersion", "Analysis", "AnalysisModel",
            "Approval", "Document", "Activity", "Breakdown", "Event",
        ],
        "AP242": [
            "Part", "PartVersion", "Assembly", "GeometricModel",
            "ShapeRepresentation", "Material", "MaterialProperty", "ComponentPlacement",
        ],
        "AP243": [
            "ExternalOwlClass", "ExternalUnit", "ExternalPropertyDefinition",
            "Classification", "ValueType",
        ],
    }

    for level, labels in level_map.items():
        for label in labels:
            neo4j.execute_query(
                f"MATCH (n:{label}) SET n.ap_level = $level, n.ap_schema = $level",
                {"level": level},
            )


def down(neo4j):
    """Remove ap_level metadata and drop indexes (best-effort)."""
    neo4j.execute_query(
        "MATCH (n) WHERE n.ap_level IS NOT NULL REMOVE n.ap_level, n.ap_schema"
    )
    # Indexes created with IF NOT EXISTS are safe to leave; drop is optional.
