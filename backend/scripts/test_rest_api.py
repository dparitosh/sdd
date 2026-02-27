#!/usr/bin/env python3
"""
REST API Test Suite for MBSE Knowledge Graph
Tests all REST API endpoints to verify functionality
"""

import json
from datetime import datetime

import requests

BASE_URL = "http://127.0.0.1:5000"


def test_endpoint(name, method, endpoint, **kwargs):
    """Test a single API endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Endpoint: {method} {endpoint}")
    print(f"{'='*60}")

    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", **kwargs)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", **kwargs)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success!")

            # Print summary of response
            if isinstance(data, dict):
                if "count" in data:
                    print(f"Results count: {data['count']}")
                if "data" in data and isinstance(data["data"], list):
                    print(f"Data items: {len(data['data'])}")
                    if len(data["data"]) > 0:
                        print(f"First item keys: {list(data['data'][0].keys())}")
                elif "openapi" in data:
                    print(f"OpenAPI Version: {data.get('openapi')}")
                    print(f"Title: {data['info']['title']}")
                    print(f"Schemas: {len(data.get('components', {}).get('schemas', {}))}")

            return True
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    """Run all API tests"""
    print(f"\n{'#'*60}")
    print(f"# MBSE Knowledge Graph REST API Test Suite")
    print(f"# Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# Base URL: {BASE_URL}")
    print(f"{'#'*60}")

    results = []

    # Test 1: Get all classes (limited)
    results.append(test_endpoint("Get All Classes", "GET", "/api/v1/Class?limit=5"))

    # Test 2: Get all packages
    results.append(test_endpoint("Get All Packages", "GET", "/api/v1/Package"))

    # Test 3: Get specific class
    results.append(
        test_endpoint(
            "Get Specific Class", "GET", "/api/v1/Class/_18_4_1_1b310459_1505839733514_450704_14138"
        )
    )

    # Test 4: Get relationships
    results.append(
        test_endpoint(
            "Get GENERALIZES Relationships", "GET", "/api/v1/relationship/GENERALIZES?limit=5"
        )
    )

    # Test 5: Execute custom query
    query_data = {"query": "MATCH (c:Class) RETURN c.name, c.id LIMIT 5", "params": {}}
    results.append(
        test_endpoint(
            "Execute Custom Cypher Query",
            "POST",
            "/api/v1/query",
            json=query_data,
            headers={"Content-Type": "application/json"},
        )
    )

    # Test 6: Get graph statistics
    results.append(test_endpoint("Get Graph Statistics", "GET", "/api/stats"))

    # Test 7: Search classes
    results.append(test_endpoint("Search Classes", "GET", "/api/v1/Class?search=Person&limit=3"))

    # Test 8: Get OpenAPI spec (just check size, don't print full content)
    print(f"\n{'='*60}")
    print(f"Testing: Get OpenAPI Specification")
    print(f"Endpoint: GET /api/openapi.json")
    print(f"{'='*60}")
    try:
        response = requests.get(f"{BASE_URL}/api/openapi.json")
        if response.status_code == 200:
            data = response.json()
            print(f"Status Code: {response.status_code}")
            print(f"✅ Success!")
            print(f"OpenAPI Version: {data.get('openapi')}")
            print(f"Title: {data['info']['title']}")
            print(f"Schemas: {len(data.get('components', {}).get('schemas', {}))}")
            print(f"Paths: {len(data.get('paths', {}))}")
            print(f"Response size: {len(response.content)} bytes")
            results.append(True)
        else:
            print(f"❌ Failed with status {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        results.append(False)

    # Print summary
    print(f"\n{'#'*60}")
    print(f"# Test Summary")
    print(f"# Total Tests: {len(results)}")
    print(f"# Passed: {sum(results)}")
    print(f"# Failed: {len(results) - sum(results)}")
    print(f"# Success Rate: {(sum(results)/len(results)*100):.1f}%")
    print(f"# Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}\n")

    if all(results):
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())
