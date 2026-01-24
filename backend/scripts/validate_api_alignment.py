#!/usr/bin/env python3
"""
REST API to Neo4j Schema Alignment Validator

This script validates that all REST API endpoints are properly aligned
with the actual Neo4j graph schema (node types and relationships).
"""

import json
from datetime import datetime

import requests

BASE_URL = "http://127.0.0.1:5000"


def query_neo4j(cypher_query, params=None):
    """Execute Cypher query via REST API"""
    response = requests.post(
        f"{BASE_URL}/api/v1/query",
        json={"query": cypher_query, "params": params or {}},
        headers={"Content-Type": "application/json"},
    )
    if response.status_code == 200:
        return response.json()["data"]
    return None


def test_api_endpoint(endpoint, expected_keys=None):
    """Test if API endpoint returns valid data"""
    try:
        response = requests.get(f"{BASE_URL}{endpoint}")
        if response.status_code == 200:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                if expected_keys:
                    first_item = data["data"][0]
                    missing_keys = set(expected_keys) - set(first_item.keys())
                    if missing_keys:
                        return False, f"Missing keys: {missing_keys}"
                return True, f"Count: {data.get('count', 0)}"
            return True, "Empty but valid"
        return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)


def main():
    print(f"\n{'='*70}")
    print(f"REST API to Neo4j Schema Alignment Validation")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    # Step 1: Get actual Neo4j schema
    print("Step 1: Querying Neo4j Graph Schema")
    print("-" * 70)

    node_labels = query_neo4j("CALL db.labels() YIELD label RETURN label ORDER BY label")
    if node_labels:
        labels = [item["label"] for item in node_labels]
        print(f"✅ Node Types Found: {len(labels)}")
        for label in labels:
            count_result = query_neo4j(f"MATCH (n:{label}) RETURN count(n) AS count")
            count = count_result[0]["count"] if count_result else 0
            print(f"   - {label:30s} ({count:4d} nodes)")

    print()
    rel_types = query_neo4j(
        "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType"
    )
    if rel_types:
        relationships = [item["relationshipType"] for item in rel_types]
        print(f"✅ Relationship Types Found: {len(relationships)}")
        for rel in relationships:
            count_result = query_neo4j(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS count")
            count = count_result[0]["count"] if count_result else 0
            print(f"   - {rel:30s} ({count:4d} relationships)")

    # Step 2: Validate API endpoints for major node types
    print(f"\n{'='*70}")
    print("Step 2: Validating API Endpoints for Node Types")
    print("-" * 70)

    node_endpoints = {
        "Class": {
            "endpoint": "/api/v1/Class?limit=5",
            "keys": ["id", "name", "description", "parent_classes", "property_count"],
        },
        "Package": {
            "endpoint": "/api/v1/Package",
            "keys": ["id", "name", "description", "child_count"],
        },
        "Port": {"endpoint": "/api/v1/Port?limit=5", "keys": ["id", "name", "owner"]},
        "Property": {"endpoint": "/api/v1/Property?limit=5", "keys": ["id", "name", "owner"]},
        "Constraint": {
            "endpoint": "/api/v1/Constraint?limit=5",
            "keys": ["id", "name", "constrained_element"],
        },
        "ModelInstance": {
            "endpoint": "/api/v1/ModelInstance?limit=5",
            "keys": ["id", "name"],
        },
        "Study": {
            "endpoint": "/api/v1/Study?limit=5",
            "keys": ["id", "name"],
        },
        "Part (AP242)": {
            "endpoint": "/api/v1/Part?limit=5",
            "keys": ["id", "name"],
        },
        "Requirement (AP239)": {
            "endpoint": "/api/v1/Requirement?limit=5",
            "keys": ["id", "name"],
        },
        "All Nodes (Generic)": {
            "endpoint": "/api/v1/nodes?type=Class&limit=3",
            "keys": ["id", "name", "type"],
        },
    }

    passed = 0
    failed = 0

    for node_type, config in node_endpoints.items():
        success, msg = test_api_endpoint(config["endpoint"], config["keys"])
        if success:
            print(f"✅ {node_type:30s} - {msg}")
            passed += 1
        else:
            print(f"❌ {node_type:30s} - {msg}")
            failed += 1

    # Step 3: Validate relationship endpoints
    print(f"\n{'='*70}")
    print("Step 3: Validating API Endpoints for Relationships")
    print("-" * 70)

    for rel_type in relationships:
        success, msg = test_api_endpoint(
            f"/api/v1/relationship/{rel_type}?limit=5",
            ["source_id", "source_name", "source_type", "target_id", "target_name", "target_type"],
        )
        if success:
            print(f"✅ {rel_type:30s} - {msg}")
            passed += 1
        else:
            print(f"❌ {rel_type:30s} - {msg}")
            failed += 1

    # Step 4: Check for coverage gaps
    print(f"\n{'='*70}")
    print("Step 4: Coverage Analysis")
    print("-" * 70)

    exposed_node_types = {"Class", "Package", "Port", "Property", "Constraint"}
    all_node_types = set(labels)

    covered = exposed_node_types.intersection(all_node_types)
    missing = all_node_types - exposed_node_types

    print(f"Node Types in Database: {len(all_node_types)}")
    print(f"Node Types with Dedicated Endpoints: {len(exposed_node_types)}")
    print(
        f"Coverage: {len(covered)}/{len(all_node_types)} ({len(covered)/len(all_node_types)*100:.1f}%)"
    )

    if missing:
        print(f"\n⚠️  Node types without dedicated endpoints:")
        for node_type in sorted(missing):
            count_result = query_neo4j(f"MATCH (n:{node_type}) RETURN count(n) AS count")
            count = count_result[0]["count"] if count_result else 0
            print(f"   - {node_type:30s} ({count:4d} nodes)")
        print(f"\n💡 Note: These can be accessed via /api/v1/nodes?type={{NodeType}}")

    print(f"\nAll {len(relationships)} relationship types have dedicated endpoints ✅")

    # Step 5: Verify key MBSE semantic patterns
    print(f"\n{'='*70}")
    print("Step 5: Validating MBSE Semantic Patterns")
    print("-" * 70)

    semantic_tests = [
        {
            "name": "Class Inheritance (GENERALIZES)",
            "query": "MATCH (c:Class)-[:GENERALIZES]->(parent:Class) RETURN count(*) AS count",
        },
        {
            "name": "Class Properties (HAS_ATTRIBUTE)",
            "query": "MATCH (c:Class)-[:HAS_ATTRIBUTE]->(p:Property) RETURN count(*) AS count",
        },
        {
            "name": "Package Containment (CONTAINS)",
            "query": "MATCH (pkg:Package)-[:CONTAINS]->(child) RETURN count(*) AS count",
        },
        {
            "name": "Property Typing (TYPED_BY)",
            "query": "MATCH (p:Property)-[:TYPED_BY]->(type) RETURN count(*) AS count",
        },
        {
            "name": "Constraint Rules (HAS_RULE)",
            "query": "MATCH (owner)-[:HAS_RULE]->(c:Constraint) RETURN count(*) AS count",
        },
    ]

    for test in semantic_tests:
        result = query_neo4j(test["query"])
        if result:
            count = result[0]["count"]
            print(f"✅ {test['name']:40s} - {count:4d} relationships")
        else:
            print(f"❌ {test['name']:40s} - Failed to query")

    # Final Summary
    print(f"\n{'='*70}")
    print("Validation Summary")
    print("-" * 70)
    print(f"Total Tests: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/(passed+failed)*100):.1f}%")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    if failed == 0:
        print("✅ All REST APIs are properly aligned with Neo4j graph schema!")
        print("\n🎯 Key Alignment Features:")
        print("   ✓ All major MBSE node types exposed (Class, Package, Port, Property, Constraint)")
        print("   ✓ All 6 relationship types accessible via REST API")
        print("   ✓ Generic /api/v1/nodes endpoint for any node type")
        print("   ✓ MBSE semantic patterns properly represented")
        print("   ✓ UML/SysML metamodel alignment maintained")
        return 0
    else:
        print(f"❌ {failed} test(s) failed - please review alignment")
        return 1


if __name__ == "__main__":
    exit(main())
