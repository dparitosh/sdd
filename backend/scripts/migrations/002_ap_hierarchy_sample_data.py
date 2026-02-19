"""
Migration 002: AP hierarchy sample data
Creates sample AP239/AP242/AP243 nodes and cross-level relationships.
Uses MERGE for idempotent re-runs.
"""


def up(neo4j):
    """Create sample AP hierarchy data with cross-level relationships."""

    # ---- AP239 sample nodes ------------------------------------------------
    neo4j.execute_query("""
        MERGE (req:Requirement {id: 'REQ-001'})
        ON CREATE SET
            req.name = 'Maximum Operating Temperature',
            req.description = 'System shall operate continuously at temperatures up to 85°C',
            req.type = 'Performance', req.priority = 'High', req.status = 'Approved',
            req.ap_level = 'AP239', req.ap_schema = 'AP239', req.created_at = datetime()
    """)
    neo4j.execute_query("""
        MERGE (rv:RequirementVersion {version: '1.2', name: 'Maximum Operating Temperature v1.2'})
        ON CREATE SET
            rv.description = 'Updated thermal requirement with extended range',
            rv.status = 'Current', rv.ap_level = 'AP239', rv.ap_schema = 'AP239',
            rv.created_at = datetime()
    """)
    neo4j.execute_query("""
        MERGE (ana:Analysis {name: 'Thermal Analysis - Steady State'})
        ON CREATE SET
            ana.type = 'ThermalSimulation', ana.method = 'Finite Element Method',
            ana.status = 'Completed', ana.ap_level = 'AP239', ana.ap_schema = 'AP239',
            ana.created_at = datetime()
    """)
    neo4j.execute_query("""
        MERGE (m:AnalysisModel {name: 'Thermal FEM Model - Rev A'})
        ON CREATE SET m.mesh_size = 5000, m.solver = 'ANSYS Mechanical',
            m.ap_level = 'AP239', m.ap_schema = 'AP239'
    """)
    neo4j.execute_query("""
        MERGE (a:Approval {name: 'Design Review Board Approval'})
        ON CREATE SET a.status = 'Approved', a.approved_by = 'Engineering Director',
            a.approval_date = date('2024-01-15'), a.ap_level = 'AP239', a.ap_schema = 'AP239'
    """)
    neo4j.execute_query("""
        MERGE (d:Document {name: 'System Requirements Specification'})
        ON CREATE SET d.document_id = 'SRS-2024-001', d.version = '2.0',
            d.type = 'Specification', d.ap_level = 'AP239', d.ap_schema = 'AP239'
    """)

    # ---- AP242 sample nodes ------------------------------------------------
    neo4j.execute_query("""
        MERGE (p:Part {id: 'PRT-1001'})
        ON CREATE SET p.name = 'Heat Sink Assembly',
            p.description = 'Aluminum heat sink with thermal interface',
            p.part_number = 'HS-AL-500', p.status = 'Released',
            p.ap_level = 'AP242', p.ap_schema = 'AP242', p.created_at = datetime()
    """)
    neo4j.execute_query("""
        MERGE (pv:PartVersion {version: 'B', name: 'Heat Sink Assembly Rev B'})
        ON CREATE SET pv.status = 'Current', pv.ap_level = 'AP242', pv.ap_schema = 'AP242'
    """)
    neo4j.execute_query("""
        MERGE (a:Assembly {name: 'Cooling System Assembly'})
        ON CREATE SET a.assembly_type = 'Mechanical', a.component_count = 5,
            a.ap_level = 'AP242', a.ap_schema = 'AP242'
    """)
    neo4j.execute_query("""
        MERGE (g:GeometricModel {name: 'Heat Sink CAD Model'})
        ON CREATE SET g.model_type = 'Solid', g.units = 'millimeters',
            g.ap_level = 'AP242', g.ap_schema = 'AP242'
    """)
    neo4j.execute_query("""
        MERGE (s:ShapeRepresentation {name: 'Heat Sink External Shape'})
        ON CREATE SET s.representation_type = 'BRep',
            s.ap_level = 'AP242', s.ap_schema = 'AP242'
    """)
    neo4j.execute_query("""
        MERGE (m:Material {name: 'Aluminum 6061-T6'})
        ON CREATE SET m.material_type = 'Metal', m.specification = 'ASTM B221',
            m.ap_level = 'AP242', m.ap_schema = 'AP242'
    """)
    neo4j.execute_query("""
        MERGE (mp:MaterialProperty {name: 'Thermal Conductivity'})
        ON CREATE SET mp.value = 167.0, mp.unit = 'W/(m·K)', mp.temperature = 20.0,
            mp.ap_level = 'AP242', mp.ap_schema = 'AP242'
    """)

    # ---- AP243 sample nodes ------------------------------------------------
    neo4j.execute_query("""
        MERGE (o:ExternalOwlClass {name: 'ThermalMaterial'})
        ON CREATE SET o.ontology = 'EMMO (Elementary Multiperspective Material Ontology)',
            o.uri = 'http://emmo.info/emmo#EMMO_ThermalMaterial',
            o.description = 'Material with defined thermal properties',
            o.ap_level = 'AP243', o.ap_schema = 'AP243'
    """)
    neo4j.execute_query("""
        MERGE (u:ExternalUnit {symbol: 'W/(m·K)'})
        ON CREATE SET u.name = 'Watt per meter Kelvin',
            u.unit_type = 'ThermalConductivity', u.si_conversion = 1.0,
            u.ap_level = 'AP243', u.ap_schema = 'AP243'
    """)
    neo4j.execute_query("""
        MERGE (u:ExternalUnit {symbol: '°C'})
        ON CREATE SET u.name = 'Degree Celsius',
            u.unit_type = 'Temperature', u.si_conversion = 1.0,
            u.ap_level = 'AP243', u.ap_schema = 'AP243'
    """)
    neo4j.execute_query("""
        MERGE (c:Classification {name: 'Thermal Management Components'})
        ON CREATE SET c.classification_system = 'ISO 13584-501', c.code = 'TMC-100',
            c.ap_level = 'AP243', c.ap_schema = 'AP243'
    """)
    neo4j.execute_query("""
        MERGE (v:ValueType {name: 'TemperatureValue'})
        ON CREATE SET v.data_type = 'double', v.unit_reference = 'degC',
            v.ap_level = 'AP243', v.ap_schema = 'AP243'
    """)

    # ---- Internal relationships (all MERGE) ---------------------------------
    _rels = [
        # AP239 internal
        ("Requirement {id: 'REQ-001'}", "RequirementVersion {version: '1.2'}", "HAS_VERSION"),
        ("Requirement {id: 'REQ-001'}", "Analysis {name: 'Thermal Analysis - Steady State'}", "VERIFIES"),
        ("Analysis {name: 'Thermal Analysis - Steady State'}", "AnalysisModel {name: 'Thermal FEM Model - Rev A'}", "USES_MODEL"),
        ("Requirement {id: 'REQ-001'}", "Approval {name: 'Design Review Board Approval'}", "APPROVES"),
        ("Document {name: 'System Requirements Specification'}", "Requirement {id: 'REQ-001'}", "DOCUMENTS"),
        # AP242 internal
        ("Part {id: 'PRT-1001'}", "PartVersion {version: 'B'}", "HAS_VERSION"),
        ("Assembly {name: 'Cooling System Assembly'}", "Part {id: 'PRT-1001'}", "ASSEMBLES_WITH"),
        ("Part {id: 'PRT-1001'}", "GeometricModel {name: 'Heat Sink CAD Model'}", "HAS_GEOMETRY"),
        ("GeometricModel {name: 'Heat Sink CAD Model'}", "ShapeRepresentation {name: 'Heat Sink External Shape'}", "HAS_REPRESENTATION"),
        ("Part {id: 'PRT-1001'}", "Material {name: 'Aluminum 6061-T6'}", "USES_MATERIAL"),
        ("Material {name: 'Aluminum 6061-T6'}", "MaterialProperty {name: 'Thermal Conductivity'}", "HAS_PROPERTY"),
        # AP243 internal
        ("Material {name: 'Aluminum 6061-T6'}", "ExternalOwlClass {name: 'ThermalMaterial'}", "CLASSIFIED_AS"),
        ("MaterialProperty {name: 'Thermal Conductivity'}", "ExternalUnit {symbol: 'W/(m·K)'}", "HAS_UNIT"),
        ("Part {id: 'PRT-1001'}", "Classification {name: 'Thermal Management Components'}", "CLASSIFIED_AS"),
        ("MaterialProperty {name: 'Thermal Conductivity'}", "ValueType {name: 'TemperatureValue'}", "HAS_VALUE_TYPE"),
        # Cross-level
        ("Requirement {id: 'REQ-001'}", "Part {id: 'PRT-1001'}", "SATISFIED_BY_PART"),
        ("Analysis {name: 'Thermal Analysis - Steady State'}", "Material {name: 'Aluminum 6061-T6'}", "ANALYZED_BY_MODEL"),
        ("Approval {name: 'Design Review Board Approval'}", "PartVersion {version: 'B'}", "APPROVED_FOR_VERSION"),
        ("Material {name: 'Aluminum 6061-T6'}", "ExternalOwlClass {name: 'ThermalMaterial'}", "MATERIAL_CLASSIFIED_AS"),
        ("MaterialProperty {name: 'Thermal Conductivity'}", "ExternalUnit {symbol: 'W/(m·K)'}", "USES_UNIT"),
        ("Requirement {id: 'REQ-001'}", "ExternalUnit {symbol: '°C'}", "REQUIREMENT_VALUE_TYPE"),
    ]

    for src, tgt, rel in _rels:
        neo4j.execute_query(
            f"MATCH (a:{src}) MATCH (b:{tgt}) MERGE (a)-[:{rel}]->(b)"
        )


def down(neo4j):
    """Remove sample AP hierarchy data. Does NOT remove indexes."""
    sample_ids = [
        "MATCH (n:Requirement {id: 'REQ-001'}) DETACH DELETE n",
        "MATCH (n:RequirementVersion {version: '1.2'}) DETACH DELETE n",
        "MATCH (n:Analysis {name: 'Thermal Analysis - Steady State'}) DETACH DELETE n",
        "MATCH (n:AnalysisModel {name: 'Thermal FEM Model - Rev A'}) DETACH DELETE n",
        "MATCH (n:Approval {name: 'Design Review Board Approval'}) DETACH DELETE n",
        "MATCH (n:Document {name: 'System Requirements Specification'}) DETACH DELETE n",
        "MATCH (n:Part {id: 'PRT-1001'}) DETACH DELETE n",
        "MATCH (n:PartVersion {version: 'B'}) DETACH DELETE n",
        "MATCH (n:Assembly {name: 'Cooling System Assembly'}) DETACH DELETE n",
        "MATCH (n:GeometricModel {name: 'Heat Sink CAD Model'}) DETACH DELETE n",
        "MATCH (n:ShapeRepresentation {name: 'Heat Sink External Shape'}) DETACH DELETE n",
        "MATCH (n:Material {name: 'Aluminum 6061-T6'}) DETACH DELETE n",
        "MATCH (n:MaterialProperty {name: 'Thermal Conductivity'}) DETACH DELETE n",
        "MATCH (n:ExternalOwlClass {name: 'ThermalMaterial'}) DETACH DELETE n",
        "MATCH (n:ExternalUnit {symbol: 'W/(m·K)'}) DETACH DELETE n",
        "MATCH (n:ExternalUnit {symbol: '°C'}) DETACH DELETE n",
        "MATCH (n:Classification {name: 'Thermal Management Components'}) DETACH DELETE n",
        "MATCH (n:ValueType {name: 'TemperatureValue'}) DETACH DELETE n",
    ]
    for stmt in sample_ids:
        neo4j.execute_query(stmt)
