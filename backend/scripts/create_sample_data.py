"""
Script to create sample test data for PLM and Simulation endpoints.
Adds requirements, traceability links, parameters, and constraints.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.graph.connection import Neo4jConnection
from src.utils.config import Config

config = Config()
NEO4J_URI = config.neo4j_uri
NEO4J_USER = config.neo4j_user
NEO4J_PASSWORD = config.neo4j_password


def create_sample_data():
    """Create sample data for testing"""
    conn = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    conn.connect()

    print("=" * 60)
    print("🔧 Creating Sample Test Data")
    print("=" * 60)

    # 1. Create additional requirements if they don't exist
    print("\n1. Creating Requirements...")
    requirements_data = [
        {
            "id": "_REQ_PERF_002",
            "name": "Response Time",
            "type": "uml:Requirement",
            "text": "System shall respond to user inputs within 100ms",
            "priority": "High",
            "status": "Approved",
        },
        {
            "id": "_REQ_SEC_002",
            "name": "Data Encryption",
            "type": "uml:Requirement",
            "text": "All sensitive data shall be encrypted using AES-256",
            "priority": "High",
            "status": "Approved",
        },
        {
            "id": "_REQ_FUNC_001",
            "name": "User Authentication",
            "type": "uml:Requirement",
            "text": "System shall support multi-factor authentication",
            "priority": "Medium",
            "status": "Approved",
        },
        {
            "id": "_REQ_FUNC_002",
            "name": "Data Export",
            "type": "uml:Requirement",
            "text": "System shall allow export of data in CSV and JSON formats",
            "priority": "Low",
            "status": "Draft",
        },
    ]

    for req in requirements_data:
        query = """
        MERGE (r:Requirement {id: $id})
        ON CREATE SET
            r.name = $name,
            r.type = $type,
            r.text = $text,
            r.priority = $priority,
            r.status = $status,
            r.created_on = datetime(),
            r.last_modified = datetime()
        RETURN r.id as id, r.name as name
        """
        result = conn.execute_query(query, req)
        if result:
            print(f"  ✓ Created/Updated: {result[0]['name']} ({result[0]['id']})")

    # 2. Create traceability links from requirements to existing Classes
    print("\n2. Creating Traceability Links...")

    # First, get some existing Classes
    get_classes_query = """
    MATCH (c:Class)
    RETURN c.id as id, c.name as name
    LIMIT 10
    """
    classes = conn.execute_query(get_classes_query)

    if classes:
        # Create traceability links
        traceability_links = [
            ("_REQ_PERF_002", classes[0]["id"] if len(classes) > 0 else None),
            ("_REQ_SEC_002", classes[1]["id"] if len(classes) > 1 else None),
            ("_REQ_FUNC_001", classes[2]["id"] if len(classes) > 2 else None),
            ("_REQ_FUNC_002", classes[3]["id"] if len(classes) > 3 else None),
            ("_REQ_PERF_002", classes[4]["id"] if len(classes) > 4 else None),
        ]

        for req_id, class_id in traceability_links:
            if class_id:
                query = """
                MATCH (r:Requirement {id: $req_id})
                MATCH (c:Class {id: $class_id})
                MERGE (r)-[rel:SHOULD_BE_SATISFIED_BY]->(c)
                ON CREATE SET rel.created_on = datetime()
                RETURN r.name as req_name, c.name as class_name
                """
                result = conn.execute_query(query, {"req_id": req_id, "class_id": class_id})
                if result:
                    print(f"  ✓ Linked: {result[0]['req_name']} → {result[0]['class_name']}")

    # 3. Add constraints to some Properties
    print("\n3. Creating Constraints...")

    # Get some existing Properties
    get_props_query = """
    MATCH (p:Property)
    RETURN p.id as id, p.name as name
    LIMIT 5
    """
    properties = conn.execute_query(get_props_query)

    if properties:
        for idx, prop in enumerate(properties[:3]):
            constraint_query = """
            MATCH (p:Property {id: $prop_id})
            MERGE (c:Constraint {id: $constraint_id})
            ON CREATE SET
                c.name = $constraint_name,
                c.body = $constraint_body,
                c.language = 'OCL',
                c.type = 'invariant'
            MERGE (p)-[r:HAS_RULE]->(c)
            RETURN c.name as name
            """

            constraint_data = {
                "prop_id": prop["id"],
                "constraint_id": f"_CONSTRAINT_{idx+1}",
                "constraint_name": f'Validate_{prop["name"]}',
                "constraint_body": f'self.{prop["name"]} <> null and self.{prop["name"]}.size() > 0',
            }

            result = conn.execute_query(constraint_query, constraint_data)
            if result:
                print(f"  ✓ Added constraint: {result[0]['name']} to {prop['name']}")

    # 4. Add parameters metadata to Properties
    print("\n4. Enhancing Properties with simulation metadata...")

    if properties:
        for prop in properties:
            update_query = """
            MATCH (p:Property {id: $prop_id})
            SET p.lower = COALESCE(p.lower, 1),
                p.upper = COALESCE(p.upper, 1),
                p.defaultValue = COALESCE(p.defaultValue, '0'),
                p.isDerived = COALESCE(p.isDerived, false),
                p.isReadOnly = COALESCE(p.isReadOnly, false)
            RETURN p.name as name
            """
            result = conn.execute_query(update_query, {"prop_id": prop["id"]})
            if result:
                print(f"  ✓ Enhanced: {result[0]['name']}")

    # 5. Create some DataTypes for units
    print("\n5. Creating Unit DataTypes...")

    unit_types = [
        {"id": "_DT_METER", "name": "Meter", "type": "uml:DataType"},
        {"id": "_DT_SECOND", "name": "Second", "type": "uml:DataType"},
        {"id": "_DT_KILOGRAM", "name": "Kilogram", "type": "uml:DataType"},
        {"id": "_DT_CELSIUS", "name": "Celsius", "type": "uml:DataType"},
        {"id": "_DT_PASCAL", "name": "Pascal", "type": "uml:DataType"},
    ]

    for unit in unit_types:
        query = """
        MERGE (dt:DataType {id: $id})
        ON CREATE SET
            dt.name = $name,
            dt.type = $type,
            dt.created_on = datetime()
        RETURN dt.name as name
        """
        result = conn.execute_query(query, unit)
        if result:
            print(f"  ✓ Created DataType: {result[0]['name']}")

    # Get final statistics
    print("\n" + "=" * 60)
    print("📊 Final Statistics")
    print("=" * 60)

    stats_queries = [
        ("Requirements", "MATCH (r:Requirement) RETURN count(r) as count"),
        ("Traceability Links", "MATCH ()-[r:SHOULD_BE_SATISFIED_BY]->() RETURN count(r) as count"),
        ("Constraints", "MATCH (c:Constraint) RETURN count(c) as count"),
        (
            "Properties with Constraints",
            "MATCH (p:Property)-[:HAS_RULE]->() RETURN count(DISTINCT p) as count",
        ),
        ("DataTypes (Units)", "MATCH (dt:DataType) RETURN count(dt) as count"),
    ]

    for label, query in stats_queries:
        result = conn.execute_query(query)
        if result:
            print(f"  • {label}: {result[0]['count']}")

    print("\n✅ Sample data creation complete!")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    create_sample_data()
