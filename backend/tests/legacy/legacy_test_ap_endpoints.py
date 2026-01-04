#!/usr/bin/env python3
"""
Test script to validate all AP239/AP242/AP243 REST API endpoints
"""

import sys
from src.web.app import app


def test_endpoints():
    """Test all new AP endpoints are registered"""

    expected_endpoints = {
        "ap239": [
            "/api/ap239/requirements",
            "/api/ap239/requirements/<req_id>",
            "/api/ap239/requirements/<req_id>/traceability",
            "/api/ap239/analyses",
            "/api/ap239/approvals",
            "/api/ap239/documents",
            "/api/ap239/statistics",
        ],
        "ap242": [
            "/api/ap242/parts",
            "/api/ap242/parts/<part_id>",
            "/api/ap242/parts/<part_id>/bom",
            "/api/ap242/assemblies",
            "/api/ap242/materials",
            "/api/ap242/materials/<material_name>",
            "/api/ap242/geometry",
            "/api/ap242/statistics",
        ],
        "ap243": [
            "/api/ap243/ontologies",
            "/api/ap243/ontologies/<ontology_name>",
            "/api/ap243/units",
            "/api/ap243/value-types",
            "/api/ap243/classifications",
            "/api/ap243/statistics",
        ],
        "hierarchy": [
            "/api/hierarchy/traceability-matrix",
            "/api/hierarchy/navigate/<node_type>/<node_id>",
            "/api/hierarchy/search",
            "/api/hierarchy/statistics",
            "/api/hierarchy/impact/<node_type>/<node_id>",
        ],
    }

    print("Testing AP239/AP242/AP243 Endpoint Registration")
    print("=" * 60)

    # Get all registered routes
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != "static":
            routes.append(str(rule))

    total_expected = 0
    total_found = 0

    for schema, endpoints in expected_endpoints.items():
        print(f"\n{schema.upper()} Endpoints:")
        print("-" * 60)

        for endpoint in endpoints:
            total_expected += 1
            # Check if endpoint pattern exists in routes
            found = any(
                endpoint.replace("<", "{").replace(">", "}") in route
                or endpoint.split("/<")[0] in route
                for route in routes
            )

            status = "✓" if found else "✗"
            print(f"  {status} {endpoint}")

            if found:
                total_found += 1

    print("\n" + "=" * 60)
    print(f"Summary: {total_found}/{total_expected} endpoints registered")

    if total_found == total_expected:
        print("✓ All AP endpoints successfully registered!")
        return 0
    else:
        print(f"✗ Missing {total_expected - total_found} endpoints")
        return 1


if __name__ == "__main__":
    sys.exit(test_endpoints())
